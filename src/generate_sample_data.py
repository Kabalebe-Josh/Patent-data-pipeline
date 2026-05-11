"""
Synthetic data generator.

Produces TSV files in the same shape as PatentsView's granted-patent
disambiguated downloads, so the rest of the pipeline can run end-to-end
without any internet access. Used when --mode sample.

Files written to data/raw/:
    g_patent.tsv
    g_inventor_disambiguated.tsv
    g_assignee_disambiguated.tsv
    g_location_disambiguated.tsv
"""
import random
from datetime import date, timedelta
from pathlib import Path

import config


# Deterministic so reruns give identical output (good for grading).
random.seed(42)


FIRST_NAMES = [
    "John", "Alice", "Wei", "Hiroshi", "Yuki", "Sven", "Olga", "Raj",
    "Mei", "Lars", "Sofia", "Diego", "Amara", "Kenji", "Priya", "Anna",
    "Carlos", "Fatima", "Liam", "Noor", "Ravi", "Emma", "Chen", "Jin",
    "Maya", "Omar", "Lina", "Daniel", "Hannah", "Tomas",
]

LAST_NAMES = [
    "Smith", "Johnson", "Wang", "Patel", "Nakamura", "Mueller", "Ivanov",
    "Garcia", "Lee", "Kim", "Lopez", "Singh", "Tanaka", "Rossi", "Dubois",
    "Anderson", "Cohen", "Okafor", "Khan", "Silva", "Petrov", "Oduya",
    "Brown", "Davis", "Park", "Wilson", "Martinez", "Sato", "Miller",
]

COUNTRIES_WEIGHTED = [
    ("US", 35), ("CN", 18), ("JP", 12), ("KR", 8), ("DE", 6),
    ("FR", 4), ("GB", 4), ("CA", 3), ("IN", 3), ("CH", 2),
    ("NL", 2), ("SE", 2), ("AU", 1),
]

COMPANY_PARTS_A = [
    "Quantum", "Helio", "Northgate", "Aether", "Polaris", "Cascade",
    "Vertex", "Oblique", "Axiom", "Lattice", "Sable", "Meridian",
    "Borealis", "Cygnus", "Sirius", "Andromeda", "Apex", "Cipher",
    "Nimbus", "Orion", "Vega", "Lyra", "Phoenix", "Crescent",
    "Argon", "Kelvin", "Tesla", "Faraday", "Edison", "Newton",
    "Halcyon", "Zephyr", "Auriga", "Caldera", "Drift", "Echo",
    "Forge", "Glacier", "Helix", "Ion", "Junction", "Kestrel",
]
COMPANY_PARTS_B = [
    "Labs", "Systems", "Industries", "Technologies", "Dynamics",
    "Robotics", "Bioscience", "Networks", "Materials", "Photonics",
    "Holdings", "Group", "Corp", "Ltd", "Solutions",
    "Innovations", "Research", "Sciences", "Devices", "Computing",
    "Therapeutics", "Semiconductors", "Aerospace", "Energy", "Logistics",
]
# Defensive: the while-loop in generate() needs at least this many possible
# unique names. We cap n_companies to this if config asks for more.
_MAX_UNIQUE_COMPANIES = len(COMPANY_PARTS_A) * len(COMPANY_PARTS_B)

PATENT_TOPICS = [
    "method for", "apparatus for", "system and method for",
    "device for", "process for", "composition for",
]

PATENT_TOPIC_TARGETS = [
    "battery thermal management",
    "neural network compression",
    "wireless power transfer",
    "autonomous vehicle perception",
    "drug delivery via nanoparticles",
    "low-latency video coding",
    "carbon capture using metal-organic frameworks",
    "quantum error correction",
    "OLED display fabrication",
    "edge computing resource scheduling",
    "lidar point-cloud filtering",
    "5G beamforming optimization",
    "gene editing with CRISPR variants",
    "solid-state battery electrolyte",
    "image super-resolution",
    "speech-to-text noise robustness",
    "satellite collision avoidance",
    "wearable biosensor",
    "secure multi-party computation",
    "robotic grasp planning",
]


def _weighted_country() -> str:
    pool = []
    for c, w in COUNTRIES_WEIGHTED:
        pool.extend([c] * w)
    return random.choice(pool)


def _random_date(start_year: int, end_year: int) -> str:
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).isoformat()


def _make_title() -> str:
    return f"{random.choice(PATENT_TOPICS).capitalize()} {random.choice(PATENT_TOPIC_TARGETS)}"


def _make_abstract(title: str) -> str:
    return (
        f"This invention discloses {title.lower()}. The disclosed embodiments "
        "improve performance, efficiency, and reliability compared to prior art. "
        "Various aspects, configurations, and applications are described."
    )


def _write_tsv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("\t".join(header) + "\n")
        for r in rows:
            # Escape stray tabs/newlines in any string field.
            cleaned = [str(v).replace("\t", " ").replace("\n", " ") if v is not None else "" for v in r]
            f.write("\t".join(cleaned) + "\n")


def generate() -> None:
    """Generate the four TSVs in data/raw/."""
    print("[sample] generating synthetic PatentsView-shaped data...")

    n_patents = config.SAMPLE_PATENTS
    n_inventors = config.SAMPLE_INVENTORS
    n_companies = min(config.SAMPLE_COMPANIES, _MAX_UNIQUE_COMPANIES)
    if n_companies < config.SAMPLE_COMPANIES:
        print(
            f"[sample]   note: capped n_companies to {n_companies} "
            f"(unique two-part name combinations available)"
        )

    min_year = config.MIN_YEAR or 2018
    max_year = config.MAX_YEAR or 2024

    # --- locations: one per country in our pool, plus a few generic ones --
    location_rows = []
    location_ids_by_country: dict[str, list[str]] = {}
    loc_counter = 0
    for country, _ in COUNTRIES_WEIGHTED:
        # Two locations per country to add a bit of variety.
        for _ in range(2):
            loc_counter += 1
            loc_id = f"loc_{loc_counter:05d}"
            location_rows.append([
                loc_id,
                f"City{loc_counter}",     # disambig_city
                f"State{loc_counter % 50}",  # disambig_state
                country,                  # disambig_country
            ])
            location_ids_by_country.setdefault(country, []).append(loc_id)

    _write_tsv(
        config.RAW_DIR / "g_location_disambiguated.tsv",
        ["location_id", "disambig_city", "disambig_state", "disambig_country"],
        location_rows,
    )
    print(f"[sample]   locations: {len(location_rows)}")

    # --- inventors (one row per unique inventor, gives us the population) --
    # PatentsView's actual inventor file has one row per (patent, inventor),
    # but we'll generate that join later. Here we fabricate the population
    # of unique inventors first.
    inventor_pop = []
    for i in range(n_inventors):
        inv_id = f"inv_{i:06d}"
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        country = _weighted_country()
        loc_id = random.choice(location_ids_by_country[country])
        inventor_pop.append({
            "inventor_id": inv_id,
            "first": first,
            "last": last,
            "location_id": loc_id,
        })

    # --- companies (population) --
    company_pop = []
    seen = set()
    while len(company_pop) < n_companies:
        name = f"{random.choice(COMPANY_PARTS_A)} {random.choice(COMPANY_PARTS_B)}"
        if name in seen:
            continue
        seen.add(name)
        company_pop.append({
            "assignee_id": f"asg_{len(company_pop):05d}",
            "organization": name,
        })

    # --- patents + the inventor/assignee relationships --
    patent_rows = []
    application_rows = []     # one row per patent, holds the real filing_date
    inventor_rows = []        # one row per (patent, inventor)
    assignee_rows = []        # one row per (patent, assignee)

    for p in range(n_patents):
        patent_id = f"{10_000_000 + p}"
        title = _make_title()
        # Filing date is what the brief schema wants; the patent (grant) date
        # is typically 1-3 years later. We model that gap loosely.
        filing_date = _random_date(min_year, max_year)
        patent_rows.append([
            patent_id,
            "utility",
            title,
            _make_abstract(title),
            filing_date,                       # patent_date (grant) — same as filing for sample simplicity
            random.randint(1, 30),             # num_claims
        ])
        application_rows.append([
            patent_id,
            f"app_{p:07d}",                    # application_id
            filing_date,                       # filing_date
        ])

        # 1-4 inventors per patent
        for inv in random.sample(inventor_pop, k=random.randint(1, 4)):
            inventor_rows.append([
                patent_id,
                inv["inventor_id"],
                inv["first"],
                inv["last"],
                inv["location_id"],
            ])

        # 0-2 assignees per patent (some patents have no company)
        n_asg = random.choices([0, 1, 2], weights=[1, 8, 2])[0]
        if n_asg:
            for asg in random.sample(company_pop, k=n_asg):
                assignee_rows.append([
                    patent_id,
                    asg["assignee_id"],
                    asg["organization"],
                    "2",  # assignee_type=2 = US company/organization
                ])

    _write_tsv(
        config.RAW_DIR / "g_patent.tsv",
        ["patent_id", "patent_type", "patent_title", "patent_abstract",
         "patent_date", "num_claims"],
        patent_rows,
    )
    print(f"[sample]   patents: {len(patent_rows)}")

    _write_tsv(
        config.RAW_DIR / "g_application.tsv",
        ["patent_id", "application_id", "filing_date"],
        application_rows,
    )
    print(f"[sample]   applications: {len(application_rows)}")

    _write_tsv(
        config.RAW_DIR / "g_inventor_disambiguated.tsv",
        ["patent_id", "inventor_id",
         "disambig_inventor_name_first", "disambig_inventor_name_last",
         "location_id"],
        inventor_rows,
    )
    print(f"[sample]   inventor rows: {len(inventor_rows)}")

    _write_tsv(
        config.RAW_DIR / "g_assignee_disambiguated.tsv",
        ["patent_id", "assignee_id", "disambig_assignee_organization",
         "assignee_type"],
        assignee_rows,
    )
    print(f"[sample]   assignee rows: {len(assignee_rows)}")

    print("[sample] done.")


if __name__ == "__main__":
    generate()
