"""
Generate demo_leads.csv with realistic synthetic B2B lead data.

This script creates a CSV file with randomized but realistic lead data
for testing and demonstration purposes.

Usage:
    python -m scripts.generate_demo_data
"""

import csv
import random
from pathlib import Path
from typing import List, Dict


# Data pools for generating realistic leads
FIRST_NAMES = [
    "Sarah", "Michael", "Priya", "James", "Elena", "David", "Lisa", "Ahmed",
    "Jennifer", "Marcus", "Sophie", "Robert", "Yuki", "Carlos", "Emily",
    "Nikolai", "Isabella", "Kevin", "Rachel", "Thomas", "Mei", "Daniel",
    "Fatima", "Oliver", "Aisha", "William", "Camila", "Henrik", "Grace",
    "Patrick", "Lucia", "Ryan", "Anastasia", "Brandon", "Nadia", "Jonathan",
    "Lena", "Emma", "Diego", "Anna", "Christopher", "Yara", "Matthew",
    "Sophia", "Alex", "Victoria", "Luis", "Zara", "Nathan", "Ines"
]

LAST_NAMES = [
    "Chen", "O'Brien", "Sharma", "Thompson", "Rodriguez", "Kim", "Mueller",
    "Hassan", "Park", "Williams", "Dubois", "Jackson", "Tanaka", "Silva",
    "Watson", "Petrov", "Rossi", "Ng", "Cohen", "Anderson", "Wong", "Murphy",
    "Al-Mansoori", "Schmidt", "Okafor", "Taylor", "Santos", "Larsson",
    "O'Connor", "Fernandez", "Mitchell", "Volkov", "Lee", "Brown", "Kowalski",
    "Johnson", "Martinez", "Bergstrom", "Davis", "El-Amin", "Wilson",
    "Papadopoulos", "Zhang", "Smith", "Garcia", "Ahmed", "Robinson", "Costa"
]

COMPANIES = [
    "TechFlow Solutions", "HealthBridge Analytics", "InnoVFinance", "Manufacturing Pro",
    "EduTech Global", "StartupForge Ventures", "Retail Dynamics", "CloudOps",
    "BioMedical Innovations", "LocalRetail Solutions", "Luxury Goods", "Industrial Tech Systems",
    "JapanSoft Corporation", "BrazilFinTech", "EduPlatform Online", "TechBridge",
    "Fashion House", "Singapore Tech Hub", "HealthTech Innovations", "Legacy Manufacturing",
    "Finance Group", "SaaS Solutions", "Retail Enterprises", "Software AG",
    "AfricaTech Solutions", "Education Corporation", "LatAm Retail Group", "Nordic Manufacturing",
    "FinTech Innovations", "HealthCare Solutions", "SaaS Ventures", "RetailChain",
    "HealthCare Systems", "Manufacturing Group", "Middle East Tech", "EdTech",
    "Retail Innovations", "FinTech Alliance", "Manufacturing Solutions", "SaaS Innovators",
    "HealthTech", "Consulting Partners", "Tech Solutions", "FinTech Corp",
    "Retail Group", "SaaS Innovations", "HealthCare Group", "Manufacturing Excellence"
]

COMPANY_SUFFIXES = [
    "Inc", "Corp", "LLC", "Ltd", "GmbH", "AG", "Group", "Solutions",
    "Systems", "Technologies", "Innovations", "Ventures", "Partners",
    "Enterprises", "Associates", "Consulting", "Services"
]

JOB_TITLES = [
    "VP of Sales", "Director of Operations", "Head of Customer Success",
    "Operations Manager", "Chief Marketing Officer", "Founder & CEO",
    "Sales Director", "VP of Engineering", "Head of Business Development",
    "Marketing Manager", "Customer Experience Lead", "VP of Growth",
    "CTO", "Sales Manager", "Co-Founder", "Director of IT",
    "VP of Customer Acquisition", "Head of Sales Operations", "CEO",
    "VP of Business Development", "Head of Digital", "Head of Marketing",
    "VP of Admissions", "Marketing Director", "Operations Director",
    "Head of Sales", "Regional Manager", "Director of Partnerships",
    "Head of Growth", "VP of Customer Success", "Senior Consultant",
    "Director of Growth", "VP of Operations", "Head of International",
    "Head of E-commerce", "Head of Enrollment"
]

INDUSTRIES = [
    "SaaS", "Healthcare", "Fintech", "Manufacturing", "Retail", "Education",
    "Technology", "Consulting", "E-commerce", "Financial Services"
]

COMPANY_SIZES = [
    "1-10", "11-50", "51-200", "201-500", "501-1000", "1001-5000", "5000+"
]

COUNTRIES = [
    "USA", "UK", "Germany", "France", "Spain", "Canada", "Australia",
    "Singapore", "Japan", "Brazil", "India", "UAE", "Netherlands",
    "Sweden", "Ireland", "Mexico", "South Korea", "Israel", "Norway"
]

SOURCES = [
    "website", "referral", "linkedin", "google_ads", "webinar", "conference",
    "trade_show", "partner", "cold_email", "content_download", "demo_request"
]

BUDGET_RANGES = [
    "under_10k", "10k-25k", "25k-50k", "50k-100k", "over_100k"
]

PAIN_POINTS = [
    "Poor lead conversion rates",
    "Data integration challenges",
    "Customer onboarding bottleneck",
    "Lead tracking inefficiency",
    "Low email engagement",
    "Manual lead qualification",
    "Omnichannel lead management",
    "API integration complexity",
    "Compliance-heavy processes",
    "Seasonal lead fluctuations",
    "High-touch customer expectations",
    "Long sales cycles",
    "Multi-language support needs",
    "Regulatory reporting overhead",
    "Student inquiry management",
    "Legacy system integration",
    "International lead distribution",
    "Data quality issues",
    "Limited resources for sales",
    "Digital transformation lag",
    "Cross-border lead handling",
    "Outbound email deliverability",
    "E-commerce integration gaps",
    "Enterprise lead complexity",
    "Limited budget constraints",
    "Multi-campus coordination",
    "Language and timezone challenges",
    "Sustainability reporting needs",
    "Mobile-first requirements",
    "GDPR compliance complexity",
    "Multilingual team coordination",
    "Franchise lead distribution",
    "Telemedicine lead influx",
    "Quote request overload",
    "Market entry challenges",
    "Virtual learning lead surge",
    "Partnership lead tracking",
    "Patient privacy requirements",
    "Client lead overflow"
]

URGENCY_LEVELS = ["low", "medium", "high"]

LEAD_MESSAGE_TEMPLATES = [
    "We're struggling with {pain_point}. Our team needs a solution urgently.",
    "Looking for help with {pain_point}. Can you help us?",
    "We've been dealing with {pain_point} for months. Ready to make a change.",
    "Our current system can't handle {pain_point}. Need automation ASAP.",
    "Interested in learning how you solve {pain_point} for {industry} companies.",
    "Saw your webinar on lead automation. We're experiencing {pain_point}.",
    "Referred by a colleague. We need help with {pain_point}.",
    "Downloaded your guide. Want to discuss {pain_point} challenges we're facing.",
    "Attended your booth at the conference. Let's talk about {pain_point}.",
    "Our CEO wants us to fix {pain_point} this quarter. Can we schedule a demo?",
    "Evaluating vendors for {pain_point}. What's your approach?",
    "We're growing fast and {pain_point} is becoming critical. Need to move quickly.",
    "Small team, big ambitions. {pain_point} is holding us back.",
    "Enterprise company looking for scalable solution for {pain_point}.",
    "Currently using spreadsheets for everything. {pain_point} is our biggest issue."
]


def generate_email(first_name: str, last_name: str, company: str) -> str:
    """Generate a realistic corporate email address."""
    # Clean company name for domain
    company_clean = company.lower()
    for suffix in ["inc", "corp", "llc", "ltd", "gmbh", "ag", "group"]:
        company_clean = company_clean.replace(f" {suffix}", "")
    company_clean = company_clean.replace(" ", "").replace("'", "")

    # Occasional personal email (10% chance)
    if random.random() < 0.1:
        domains = ["gmail.com", "outlook.com", "yahoo.com"]
        return f"{first_name.lower()}.{last_name.lower()}@{random.choice(domains)}"

    # Corporate email patterns
    patterns = [
        f"{first_name.lower()}.{last_name.lower()}",
        f"{first_name[0].lower()}{last_name.lower()}",
        f"{first_name.lower()}",
        f"{first_name.lower()}_{last_name.lower()}"
    ]

    # Domain suffixes
    suffixes = [".com", ".io", ".co", ".ai", ".tech", ".solutions", ".group"]

    username = random.choice(patterns)
    domain = company_clean + random.choice(suffixes)

    return f"{username}@{domain}"


def generate_phone(country: str) -> str:
    """Generate a realistic phone number based on country."""
    phone_formats = {
        "USA": lambda: f"+1-555-{random.randint(0, 9999):04d}",
        "UK": lambda: f"+44-{random.randint(10, 99)}-{random.randint(1000000, 9999999)}",
        "Germany": lambda: f"+49-{random.randint(10, 999)}-{random.randint(100000, 9999999)}",
        "France": lambda: f"+33-{random.randint(1, 9)}-{random.randint(1000000, 9999999)}",
        "Spain": lambda: f"+34-{random.randint(10, 99)}-{random.randint(1000000, 9999999)}",
        "Canada": lambda: f"+1-{random.randint(100, 999)}-555-{random.randint(0, 9999):04d}",
        "Australia": lambda: f"+61-{random.randint(1, 9)}-{random.randint(1000000, 9999999)}",
        "Singapore": lambda: f"+65-{random.randint(1000, 9999)}-{random.randint(0, 9999):04d}",
        "Japan": lambda: f"+81-{random.randint(1, 9)}-{random.randint(1000000, 9999999)}",
        "Brazil": lambda: f"+55-{random.randint(10, 99)}-{random.randint(1000000, 9999999)}",
        "India": lambda: f"+91-{random.randint(10, 99)}-{random.randint(1000000, 9999999)}",
        "UAE": lambda: f"+971-{random.randint(1, 9)}-{random.randint(100000, 9999999)}",
    }

    formatter = phone_formats.get(country, lambda: f"+1-555-{random.randint(0, 9999):04d}")
    return formatter()


def generate_lead() -> Dict[str, str]:
    """Generate a single realistic lead."""
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    company = random.choice(COMPANIES)
    if random.random() < 0.3:  # 30% chance of having suffix
        company += " " + random.choice(COMPANY_SUFFIXES)

    country = random.choice(COUNTRIES)
    pain_point = random.choice(PAIN_POINTS)
    industry = random.choice(INDUSTRIES)

    # Weight budget ranges (fewer very small and very large)
    budget_weights = [0.1, 0.2, 0.4, 0.2, 0.1]
    budget_range = random.choices(BUDGET_RANGES, weights=budget_weights)[0]

    # Weight urgency (more medium, some high, less low)
    urgency_weights = [0.2, 0.5, 0.3]
    urgency = random.choices(URGENCY_LEVELS, weights=urgency_weights)[0]

    # Generate lead message
    message_template = random.choice(LEAD_MESSAGE_TEMPLATES)
    lead_message = message_template.format(pain_point=pain_point.lower(), industry=industry)

    # Occasionally add more detail (30% chance)
    if random.random() < 0.3:
        extra_details = [
            " We're looking to implement within the next quarter.",
            " Budget is approved, just need the right solution.",
            " Our team is ready to move quickly on this.",
            " We've evaluated a few vendors but haven't found the right fit yet.",
            " This is a top priority for our leadership team."
        ]
        lead_message += random.choice(extra_details)

    return {
        "first_name": first_name,
        "last_name": last_name,
        "email": generate_email(first_name, last_name, company),
        "phone": generate_phone(country),
        "company_name": company,
        "job_title": random.choice(JOB_TITLES),
        "industry": industry,
        "company_size": random.choice(COMPANY_SIZES),
        "country": country,
        "source": random.choice(SOURCES),
        "budget_range": budget_range,
        "pain_point": pain_point,
        "urgency": urgency,
        "lead_message": lead_message
    }


def add_edge_cases(leads: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Add edge case leads for testing."""
    edge_cases = [
        {
            "first_name": "=Trevor",
            "last_name": "Malicious",
            "email": "trevor@hackme.com",
            "phone": "+1-555-9999",
            "company_name": "Hack Attempt Inc",
            "job_title": "Hacker",
            "industry": "Technology",
            "company_size": "1-10",
            "country": "USA",
            "source": "dark_web",
            "budget_range": "under_10k",
            "pain_point": "CSV injection test",
            "urgency": "low",
            "lead_message": "This is a test for CSV injection with leading equals sign"
        },
        {
            "first_name": "John",
            "last_name": "Smith",
            "email": "john.smith@example",  # Missing domain
            "phone": "+1-555-8888",
            "company_name": "No Domain Corp",
            "job_title": "Manager",
            "industry": "Retail",
            "company_size": "11-50",
            "country": "USA",
            "source": "website",
            "budget_range": "10k-25k",
            "pain_point": "Missing email domain",
            "urgency": "medium",
            "lead_message": "This lead has an incomplete email address for testing validation"
        },
        {
            "first_name": "Alice",
            "last_name": "Wonderland",
            "email": "alice@reallylongcompanynamewithtoomanycharactersandspecialchars!!!.com",
            "phone": "+44-20-7777777",
            "company_name": "Company With Super Ultra Mega Long Name That Goes On Forever And Ever",
            "job_title": "Chief Everything Officer of All Departments",
            "industry": "Industry",
            "company_size": "51-200",
            "country": "UK",
            "source": "website",
            "budget_range": "25k-50k",
            "pain_point": "Testing long values",
            "urgency": "low",
            "lead_message": "This is an extremely long lead message that goes on and on and on to test how the system handles very verbose input from leads who write essays instead of concise messages."
        },
        {
            "first_name": "Bob",
            "last_name": "O'Reilly-Smith",
            "email": "bob@test.com",
            "phone": "",  # Empty phone
            "company_name": "Empty Phone Company",
            "job_title": "VP",
            "industry": "SaaS",
            "company_size": "",  # Empty size
            "country": "",  # Empty country
            "source": "referral",
            "budget_range": "",  # Empty budget
            "pain_point": "Missing multiple fields",
            "urgency": "high",
            "lead_message": "Testing sparse data handling"
        },
        {
            "first_name": "@Maria",
            "last_name": "Plus",
            "email": "maria+test@gmail.com",
            "phone": "+1-555-7777",
            "company_name": "Gmail User Corp",
            "job_title": "Freelancer",
            "industry": "Consulting",
            "company_size": "1-10",
            "country": "USA",
            "source": "linkedin",
            "budget_range": "under_10k",
            "pain_point": "Personal email domain",
            "urgency": "low",
            "lead_message": "Testing personal email instead of corporate"
        }
    ]

    return leads + edge_cases


def generate_csv(output_path: Path, num_leads: int = 75):
    """Generate demo_leads.csv file."""
    print(f"Generating {num_leads} realistic B2B leads...")

    # Generate normal leads
    leads = [generate_lead() for _ in range(num_leads)]

    # Add edge cases
    leads = add_edge_cases(leads)

    # Write to CSV
    fieldnames = [
        "first_name", "last_name", "email", "phone", "company_name",
        "job_title", "industry", "company_size", "country", "source",
        "budget_range", "pain_point", "urgency", "lead_message"
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(leads)

    print(f"✓ Generated {len(leads)} leads ({num_leads} normal + {len(leads) - num_leads} edge cases)")
    print(f"✓ Saved to: {output_path}")

    # Print summary stats
    industries = {}
    sources = {}
    budgets = {}

    for lead in leads:
        industries[lead['industry']] = industries.get(lead['industry'], 0) + 1
        sources[lead['source']] = sources.get(lead['source'], 0) + 1
        budgets[lead['budget_range']] = budgets.get(lead['budget_range'], 0) + 1

    print("\nSummary:")
    print(f"  Industries: {len(industries)} different")
    print(f"  Sources: {len(sources)} different")
    print(f"  Budget ranges: {len(budgets)} different")
    print(f"  Countries: {len(set(lead['country'] for lead in leads if lead['country']))} different")


if __name__ == "__main__":
    output_path = Path(__file__).parent.parent / "data" / "demo_leads.csv"
    generate_csv(output_path, num_leads=75)
    print("\n✓ Done! You can now run: python -m scripts.seed_demo_data")
