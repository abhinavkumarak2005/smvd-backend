"""011 seed services and conflict rules

Revision ID: 011
Revises: 010
Create Date: 2026-06-25

NOTE: Prices marked as 10000 paise (₹100) are PLACEHOLDERS.
      Update with real temple prices before staging deployment.
"""

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None

from alembic import op

# Fixed UUIDs for all services — referenced by conflict_rules seed below.
# DO NOT change these after migration runs in any environment.
MOOLAVAR_ABISHEGAM_ID    = "11111111-1111-1111-1111-111111111001"
GANAPATHY_HOMAM_ID       = "11111111-1111-1111-1111-111111111002"
KAAPU_SANDHANA_ID        = "11111111-1111-1111-1111-111111111003"
KAAPU_VENNAI_ID          = "11111111-1111-1111-1111-111111111004"
KAVASAM_ID               = "11111111-1111-1111-1111-111111111005"
GOLD_CHARIOT_ID          = "11111111-1111-1111-1111-111111111006"
SILVER_CHARIOT_ID        = "11111111-1111-1111-1111-111111111007"
THIRUKALYANAM_ID         = "11111111-1111-1111-1111-111111111008"
ANNADHANAM_PRASADHA_ID   = "11111111-1111-1111-1111-111111111009"
ANNADHANAM_MEALS_ID      = "11111111-1111-1111-1111-111111111010"


def upgrade() -> None:
    # ── Seed 10 services ──────────────────────────────────────────────────────
    op.execute(f"""
        INSERT INTO services (
            id, name, name_tamil, category, price_paise,
            max_persons, advance_booking_days, session, sort_order
        ) VALUES
        (
            '{MOOLAVAR_ABISHEGAM_ID}',
            'Moolavar Abishegam', 'மூலவர் அபிஷேகம்',
            'archanai', 10000,
            30, 1, 'morning', 1
        ),
        (
            '{GANAPATHY_HOMAM_ID}',
            'Ganapathy Homam', 'கணபதி ஹோமம்',
            'homam', 10000,
            5, 5, 'morning', 2
        ),
        (
            '{KAAPU_SANDHANA_ID}',
            'Kaapu (Sandhana Kaappu)', 'காப்பு (சந்தன காப்பு)',
            'seva', 10000,
            5, 1, 'na', 3
        ),
        (
            '{KAAPU_VENNAI_ID}',
            'Kaapu (Vennai Kaappu)', 'காப்பு (வெண்ணை காப்பு)',
            'seva', 10000,
            5, 1, 'na', 4
        ),
        (
            '{KAVASAM_ID}',
            'Kavasam', 'கவசம்',
            'seva', 10000,
            5, 1, 'na', 5
        ),
        (
            '{GOLD_CHARIOT_ID}',
            'Gold Chariot', 'தங்க தேர்',
            'chariot', 10000,
            1, 1, 'both', 6
        ),
        (
            '{SILVER_CHARIOT_ID}',
            'Silver Chariot', 'வெள்ளி தேர்',
            'chariot', 10000,
            1, 1, 'both', 7
        ),
        (
            '{THIRUKALYANAM_ID}',
            'Urchavar Thirukalyanam', 'உற்சவர் திருக்கல்யாணம்',
            'special', 10000,
            5, 1, 'morning', 8
        ),
        (
            '{ANNADHANAM_PRASADHA_ID}',
            'Annadhanam (Prasadha Thonnai)', 'அன்னதானம் (பிரசாத தொன்னை)',
            'annadhanam', 10000,
            5, 1, 'na', 9
        ),
        (
            '{ANNADHANAM_MEALS_ID}',
            'Annadhanam (Meals)', 'அன்னதானம் (உணவு)',
            'annadhanam', 10000,
            1, 1, 'na', 10
        )
        ON CONFLICT (id) DO NOTHING;
    """)

    # ── Seed conflict rules ───────────────────────────────────────────────────
    op.execute(f"""
        INSERT INTO conflict_rules (
            service_a_id, service_b_id, rule_type, direction, notice_text
        ) VALUES
        (
            '{KAAPU_SANDHANA_ID}', '{KAVASAM_ID}',
            'mutual_exclusion', 'bidirectional',
            'Kaapu (Sandhana) and Kavasam cannot be booked on the same date.'
        ),
        (
            '{KAAPU_VENNAI_ID}', '{KAVASAM_ID}',
            'mutual_exclusion', 'bidirectional',
            'Kaapu (Vennai) and Kavasam cannot be booked on the same date.'
        ),
        (
            '{THIRUKALYANAM_ID}', '{GOLD_CHARIOT_ID}',
            'a_blocks_b', 'a_to_b',
            'Gold Chariot morning session is not available when Thirukalyanam is scheduled.'
        ),
        (
            '{GANAPATHY_HOMAM_ID}', '{GOLD_CHARIOT_ID}',
            'requires_approval', 'a_to_b',
            'Ganapathy Homam is also scheduled on this date. Your booking requires admin approval.'
        )
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    # Remove seeded conflict rules
    op.execute(f"""
        DELETE FROM conflict_rules
        WHERE service_a_id IN (
            '{KAAPU_SANDHANA_ID}','{KAAPU_VENNAI_ID}',
            '{THIRUKALYANAM_ID}','{GANAPATHY_HOMAM_ID}'
        );
    """)
    # Remove seeded services
    op.execute(f"""
        DELETE FROM services WHERE id IN (
            '{MOOLAVAR_ABISHEGAM_ID}','{GANAPATHY_HOMAM_ID}',
            '{KAAPU_SANDHANA_ID}','{KAAPU_VENNAI_ID}','{KAVASAM_ID}',
            '{GOLD_CHARIOT_ID}','{SILVER_CHARIOT_ID}','{THIRUKALYANAM_ID}',
            '{ANNADHANAM_PRASADHA_ID}','{ANNADHANAM_MEALS_ID}'
        );
    """)
