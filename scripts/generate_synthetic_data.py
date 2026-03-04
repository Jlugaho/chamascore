"""
ChamaScore Synthetic Data Seeder
Populates the SQLite database with realistic chama data for demo purposes.
Run from: ~/chamascore/backend
Usage: python ../scripts/generate_synthetic_data.py
"""
import sys
import os
import uuid
import random
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine
from app.core.security import get_password_hash
from app.models.models import Base, User, Group, GroupMember, Contribution, Loan, LoanRepayment, Meeting, MeetingAttendance

# ── Seed ──────────────────────────────────────────────────────────────────────
random.seed(42)

KENYAN_NAMES = [
    "Wanjiku Kamau", "John Mwangi", "Grace Otieno", "Peter Njoroge",
    "Mary Achieng", "James Kibet", "Faith Mutua", "David Odhiambo",
    "Rose Wambua", "Samuel Kariuki", "Agnes Njeri", "Daniel Onyango",
    "Alice Wangari", "Joseph Ndirangu", "Lucy Adhiambo", "Michael Owuor",
    "Esther Kimani", "George Macharia", "Beatrice Auma", "Paul Karanja",
]

LOAN_PURPOSES = [
    "School fees", "Business expansion", "Medical emergency",
    "Farm inputs", "Equipment purchase", "House repair",
    "Wedding expenses", "Transport business", "Stock replenishment",
]

def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))

def seed():
    db = SessionLocal()
    
    print("\n🏦 ChamaScore Data Seeder")
    print("=" * 40)

    # ── Create demo user ──────────────────────────────────────────────────────
    print("→ Creating demo user...")
    demo_user = db.query(User).filter(User.email == "demo@chamascore.co.ke").first()
    if not demo_user:
        demo_user = User(
            id=str(uuid.uuid4()),
            email="demo@chamascore.co.ke",
            phone="0700000001",
            national_id="11111111",
            full_name="Demo User",
            password_hash=get_password_hash("Demo1234"),
        )
        db.add(demo_user)
        db.commit()
        print("  ✓ Demo user created — email: demo@chamascore.co.ke / password: Demo1234")
    else:
        print("  ✓ Demo user already exists")

    # ── Create member users ───────────────────────────────────────────────────
    print("→ Creating members...")
    members = []
    for i, name in enumerate(KENYAN_NAMES):
        email = f"member{i+1}@chamascore.co.ke"
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            members.append(existing)
            continue
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            phone=f"07{str(i+10).zfill(2)}{'1234567'[:7]}",
            national_id=f"2{str(i+1).zfill(7)}",
            full_name=name,
            password_hash=get_password_hash("Member123"),
        )
        db.add(user)
        members.append(user)
    db.commit()
    print(f"  ✓ {len(members)} members ready")

    # ── Create two chama groups ───────────────────────────────────────────────
    print("→ Creating chama groups...")
    
    groups_data = [
        {
            "name": "Umoja Welfare Association",
            "description": "A monthly savings group focused on financial empowerment in Westlands",
            "contribution_amount": 2000,
            "meeting_frequency": "monthly",
            "meeting_day": "Saturday",
            "formed": date(2022, 3, 1),
            "member_count": 15,
            "quality": "excellent",
        },
        {
            "name": "Kilimani Savings Circle",
            "description": "A biweekly investment group focused on agribusiness opportunities",
            "contribution_amount": 1000,
            "meeting_frequency": "biweekly",
            "meeting_day": "Wednesday",
            "formed": date(2023, 6, 1),
            "member_count": 10,
            "quality": "good",
        },
    ]

    created_groups = []
    for gdata in groups_data:
        existing = db.query(Group).filter(Group.name == gdata["name"]).first()
        if existing:
            print(f"  ✓ '{gdata['name']}' already exists — skipping")
            created_groups.append((existing, gdata))
            continue

        group = Group(
            id=str(uuid.uuid4()),
            name=gdata["name"],
            description=gdata["description"],
            contribution_amount=gdata["contribution_amount"],
            meeting_frequency=gdata["meeting_frequency"],
            meeting_day=gdata["meeting_day"],
            created_date=gdata["formed"],
            created_by=demo_user.id,
        )
        db.add(group)
        db.flush()

        # Add demo user as chairperson
        db.add(GroupMember(
            id=str(uuid.uuid4()),
            user_id=demo_user.id,
            group_id=group.id,
            role="chairperson",
            joined_date=gdata["formed"],
        ))

        # Add members
        group_members = random.sample(members, gdata["member_count"] - 1)
        for i, member in enumerate(group_members):
            db.add(GroupMember(
                id=str(uuid.uuid4()),
                user_id=member.id,
                group_id=group.id,
                role="treasurer" if i == 0 else "secretary" if i == 1 else "member",
                joined_date=gdata["formed"] + timedelta(days=random.randint(0, 30)),
            ))

        db.commit()
        created_groups.append((group, gdata))
        print(f"  ✓ Created '{gdata['name']}'")

    # ── Generate contributions ────────────────────────────────────────────────
    print("→ Generating contributions...")
    total_contributions = 0

    for group, gdata in created_groups:
        existing = db.query(Contribution).filter(Contribution.group_id == group.id).count()
        if existing > 0:
            print(f"  ✓ '{group.name}' already has {existing} contributions — skipping")
            continue

        group_members = db.query(GroupMember).filter(
            GroupMember.group_id == group.id, GroupMember.is_active == True
        ).all()

        formed = gdata["formed"]
        today = date.today()
        freq_days = {"monthly": 30, "biweekly": 14, "weekly": 7}[gdata["meeting_frequency"]]
        reliability = 0.95 if gdata["quality"] == "excellent" else 0.82

        cycle_date = formed
        while cycle_date <= today:
            for gm in group_members:
                if random.random() < reliability:
                    # Slight variation for realism
                    amount = gdata["contribution_amount"]
                    if random.random() < 0.05:
                        amount = amount * 0.5  # occasional partial payment
                    db.add(Contribution(
                        id=str(uuid.uuid4()),
                        group_id=group.id,
                        member_id=gm.user_id,
                        amount=amount,
                        contribution_date=cycle_date + timedelta(days=random.randint(0, 3)),
                        payment_method=random.choices(["mpesa", "cash", "bank_transfer"], weights=[70, 25, 5])[0],
                    ))
                    total_contributions += 1
            cycle_date += timedelta(days=freq_days)

        db.commit()

    print(f"  ✓ {total_contributions} contribution records created")

    # ── Generate loans ────────────────────────────────────────────────────────
    print("→ Generating loans...")
    total_loans = 0

    for group, gdata in created_groups:
        existing = db.query(Loan).filter(Loan.group_id == group.id).count()
        if existing > 0:
            print(f"  ✓ '{group.name}' already has {existing} loans — skipping")
            continue

        group_members = db.query(GroupMember).filter(
            GroupMember.group_id == group.id
        ).all()

        formed = gdata["formed"]
        today = date.today()
        n_loans = 20 if gdata["quality"] == "excellent" else 12
        default_rate = 0.02 if gdata["quality"] == "excellent" else 0.08

        for _ in range(n_loans):
            borrower = random.choice(group_members)
            applied = random_date(formed + timedelta(days=60), today - timedelta(days=30))
            amount = gdata["contribution_amount"] * random.randint(2, 8)
            disbursed = applied + timedelta(days=random.randint(3, 10))
            repayment_due = disbursed + timedelta(days=random.randint(30, 120))

            if random.random() < default_rate:
                status = "defaulted"
            elif repayment_due > today:
                status = "active"
            else:
                status = "repaid"

            loan = Loan(
                id=str(uuid.uuid4()),
                group_id=group.id,
                member_id=borrower.user_id,
                amount=amount,
                purpose=random.choice(LOAN_PURPOSES),
                application_date=applied,
                approval_status="approved",
                disbursed_date=disbursed,
                repayment_date=repayment_due,
                interest_rate=10.0,
                status=status,
            )
            db.add(loan)
            db.flush()

            # Add repayment record for repaid loans
            if status == "repaid":
                db.add(LoanRepayment(
                    id=str(uuid.uuid4()),
                    loan_id=loan.id,
                    amount=amount * 1.1,  # principal + 10% interest
                    payment_date=repayment_due - timedelta(days=random.randint(0, 10)),
                ))

            total_loans += 1

        db.commit()

    print(f"  ✓ {total_loans} loan records created")

    # ── Generate meetings ─────────────────────────────────────────────────────
    print("→ Generating meetings...")
    total_meetings = 0

    AGENDAS = [
        "Monthly contributions review and loan applications",
        "Financial report and transparency review",
        "New member applications and vetting",
        "Loan default follow-up and resolution",
        "Planning group social event and investment review",
        "Annual general meeting and elections",
    ]

    for group, gdata in created_groups:
        existing = db.query(Meeting).filter(Meeting.group_id == group.id).count()
        if existing > 0:
            print(f"  ✓ '{group.name}' already has {existing} meetings — skipping")
            continue

        group_members = db.query(GroupMember).filter(
            GroupMember.group_id == group.id
        ).all()

        formed = gdata["formed"]
        today = date.today()
        freq_days = {"monthly": 30, "biweekly": 14, "weekly": 7}[gdata["meeting_frequency"]]
        attendance_rate = 0.90 if gdata["quality"] == "excellent" else 0.75

        meeting_date = formed
        meeting_num = 1
        while meeting_date <= today:
            meeting = Meeting(
                id=str(uuid.uuid4()),
                group_id=group.id,
                title=f"{'Monthly' if gdata['meeting_frequency'] == 'monthly' else 'Regular'} Meeting #{meeting_num}",
                date=meeting_date,
                agenda=random.choice(AGENDAS),
                minutes=f"Meeting held. {int(len(group_members) * attendance_rate)} members attended." if meeting_date < today else None,
            )
            db.add(meeting)
            db.flush()

            # Attendance records
            for gm in group_members:
                attended = random.random() < attendance_rate
                db.add(MeetingAttendance(
                    id=str(uuid.uuid4()),
                    meeting_id=meeting.id,
                    member_id=gm.user_id,
                    attended=attended,
                    fine_amount=200 if not attended else 0,
                ))

            meeting_date += timedelta(days=freq_days)
            meeting_num += 1
            total_meetings += 1

        db.commit()

    print(f"  ✓ {total_meetings} meeting records created")

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 40)
    print("✅ Seeding complete! Summary:")
    print(f"  Users        : {db.query(User).count()}")
    print(f"  Groups       : {db.query(Group).count()}")
    print(f"  Contributions: {db.query(Contribution).count()}")
    print(f"  Loans        : {db.query(Loan).count()}")
    print(f"  Meetings     : {db.query(Meeting).count()}")
    print()
    print("🔑 Login with:")
    print("  Email   : demo@chamascore.co.ke")
    print("  Password: Demo1234")
    print("=" * 40)

    db.close()

if __name__ == "__main__":
    seed()