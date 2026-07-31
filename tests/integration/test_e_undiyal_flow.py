import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock

@pytest.fixture
def fake_db():
    return {
        "e_undiyal": {},
        "payment": {},
        "certificate": {}
    }

@pytest.mark.asyncio
async def test_e_undiyal_full_flow(auth_client, admin_client, fake_db):
    user_id = "11111111-1111-1111-1111-111111111111"
    tx_id = str(uuid4())
    pay_id = str(uuid4())
    
    # 1. Mock repo behaviors
    async def mock_create_transaction(conn, data):
        record = {
            "id": tx_id,
            "user_id": data["user_id"],
            "amount_paise": data["amount_paise"],
            "donor_name": data["donor_name"],
            "donor_email": data["donor_email"],
            "donor_phone": data.get("donor_phone"),
            "pan_number": data.get("pan_number"),
            "status": "pending_payment",
            "certificate_status": "not_applicable",
            "transaction_reference": f"REF-{tx_id}"
        }
        fake_db["e_undiyal"][tx_id] = record
        return record
        
    async def mock_create_payment_record(conn, e_undiyal_id, amount_paise, **kwargs):
        record = {
            "id": pay_id,
            "e_undiyal_id": e_undiyal_id,
            "amount_paise": amount_paise,
            "status": "pending"
        }
        fake_db["payment"][pay_id] = record
        return record
        
    async def mock_get_payment(conn, gateway_order_id):
        # We'll use pay_id as gateway_order_id for simplicity
        return fake_db["payment"].get(gateway_order_id)
        
    async def mock_update_payment_status(conn, payment_id, status, gateway_payment_id):
        fake_db["payment"][payment_id]["status"] = status
        fake_db["payment"][payment_id]["gateway_payment_id"] = gateway_payment_id
        
    async def mock_update_transaction_status(conn, tx_id, status):
        tx_id_str = str(tx_id)
        fake_db["e_undiyal"][tx_id_str]["status"] = status
        if status == "success":
            fake_db["e_undiyal"][tx_id_str]["certificate_status"] = "pending_details"
            
    async def mock_get_transaction(conn, tx_id):
        return fake_db["e_undiyal"].get(str(tx_id))
        
    async def mock_update_certificate_preference(conn, tx_id, pref_data):
        tx_id_str = str(tx_id)
        fake_db["e_undiyal"][tx_id_str]["certificate_status"] = "processing"
        fake_db["certificate"][tx_id_str] = pref_data
        
    async def mock_get_certificate_status(conn, tx_id):
        txn = fake_db["e_undiyal"].get(str(tx_id))
        if txn:
            return {"certificate_status": txn.get("certificate_status", "not_applicable"), "user_id": txn.get("user_id")}
        return None
        
    async def mock_get_pending_certificates(conn):
        return [tx for tx in fake_db["e_undiyal"].values() if tx.get("certificate_status") == "processing"]
        
    async def mock_issue_certificate(conn, tx_id, cert_data, admin_id):
        tx_id_str = str(tx_id)
        fake_db["e_undiyal"][tx_id_str]["certificate_status"] = "ready"
        fake_db["certificate"][tx_id_str]["issued"] = True

    with patch("app.services.e_undiyal_service.e_undiyal_repo.create_transaction", side_effect=mock_create_transaction), \
         patch("app.services.e_undiyal_service.payment_repo.create_payment_record", side_effect=mock_create_payment_record), \
         patch("app.services.e_undiyal_service.payment_service.create_order", return_value={"id": pay_id, "payment_url": "http://pay"}), \
         patch("app.routers.e_undiyal.donate.e_undiyal_repo.get_transaction", side_effect=mock_get_transaction), \
         patch("app.services.certificate_service.e_undiyal_repo.get_transaction", side_effect=mock_get_transaction), \
         patch("app.services.certificate_service.certificate_repo.update_delivery_preference", side_effect=mock_update_certificate_preference), \
         patch("app.routers.e_undiyal.certificate.certificate_repo.get_certificate_status", side_effect=mock_get_certificate_status), \
         patch("app.services.e_undiyal_service.e_undiyal_repo.update_status", side_effect=mock_update_transaction_status), \
         patch("app.services.e_undiyal_service.payment_repo.update_payment_status", new_callable=AsyncMock), \
         patch("app.routers.admin.certificates.certificate_repo.get_pending_certificates", side_effect=mock_get_pending_certificates), \
         patch("app.routers.admin.certificates.certificate_service.issue_certificate", side_effect=mock_issue_certificate), \
         patch("app.routers.admin.certificates.notification_service.send_email", new_callable=AsyncMock):

        # 1. Initiate Donation
        req = {
            "amount_paise": 10000,
            "donor_name": "Test User",
            "donor_email": "test@example.com",
            "donor_phone": "+919999999999",
            "donation_category": "General"
        }
        res1 = auth_client.post("/api/v1/e-undiyal/initiate", json=req)
        assert res1.status_code == 201
        assert res1.json()["gateway_order_id"] == pay_id
        assert fake_db["e_undiyal"][tx_id]["status"] == "pending_payment"
        
        # 2. Simulate Webhook
        # (Since E-Undiyal webhook isn't implemented in the router yet, we simulate the DB update)
        fake_db["e_undiyal"][tx_id]["status"] = "success"
        fake_db["e_undiyal"][tx_id]["certificate_status"] = "pending_details"
        fake_db["payment"][pay_id]["status"] = "success"
        
        # 3. Get transaction status
        res3 = auth_client.get(f"/api/v1/e-undiyal/{tx_id}")
        assert res3.status_code == 200
        assert res3.json()["status"] == "success"
        assert res3.json()["certificate_status"] == "pending_details"
        
        # 4. Update preference
        res4 = auth_client.post(f"/api/v1/e-undiyal/{tx_id}/certificate-preference", json={
            "donor_location_type": "local",
            "delivery_mode": "in_person",
            "donor_address": None
        })
        assert res4.status_code == 200
        assert fake_db["e_undiyal"][tx_id]["certificate_status"] == "processing"
        
        # 5. Admin issues certificate
        res5 = admin_client.post(f"/api/v1/admin/certificates/{tx_id}/issue", json={"certificate_data": {}})
        assert res5.status_code == 200
        assert fake_db["e_undiyal"][tx_id]["certificate_status"] == "ready"
        
        # 6. Verify final status
        res6 = auth_client.get(f"/api/v1/e-undiyal/{tx_id}")
        assert res6.status_code == 200
        assert res6.json()["certificate_status"] == "ready"
