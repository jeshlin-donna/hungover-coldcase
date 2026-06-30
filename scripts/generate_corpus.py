"""
generate_corpus.py — generate 250 synthetic police incident records.
These are NOISE for the benchmark — they do NOT contain hero case signatures.

Hero-case signals intentionally excluded:
  - NO "8mm pry blade with left-side nick" (hero tool signature)
  - NO "dark blue 2015-2018 Honda Accord" (hero vehicle)
  - NO "Daniel Marsh" (hero suspect)
  - NO Maple Heights Drive / Riverside Lane / Maple Heights Court (hero addresses)

Run: python scripts/generate_corpus.py
"""
import os
import random
from pathlib import Path

random.seed(42)

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# -------- location pools --------
DEPARTMENTS = [
    "Oak Park Police Department", "Westfield Police Department",
    "Lakeview Police Department", "Glenwood Police Department",
    "Pinecrest Police Department", "Cedar Falls Police Department",
    "Harborview Police Department", "Sunridge Police Department",
    "Elmwood Police Department", "Fairview Police Department",
    "Northgate Police Department", "Southbrook Police Department",
]

STREETS = [
    "Birch Street", "Cedar Avenue", "Elm Drive", "Fern Court", "Grove Lane",
    "Hillside Road", "Ivy Way", "Juniper Circle", "Kestrel Court", "Larkspur Drive",
    "Magnolia Avenue", "Nightingale Street", "Orchard Lane", "Poplar Way",
    "Quarry Road", "Redwood Drive", "Sage Court", "Timberline Avenue",
    "Upland Way", "Valley View Road", "Willowbrook Drive", "Xerxes Avenue",
    "Yellow Pine Lane", "Zephyr Court", "Autumn Ridge Drive", "Blue Heron Way",
    "Cobblestone Lane", "Driftwood Court", "Evergreen Circle", "Foxglove Drive",
    "Garden View Avenue", "Harvest Moon Lane", "Ironwood Court", "Juniper Ridge",
]

CITIES = [
    "Oak Park", "Westfield", "Lakeview", "Glenwood", "Pinecrest",
    "Cedar Falls", "Harborview", "Sunridge", "Elmwood", "Fairview",
    "Northgate", "Southbrook",
]

OFFICERS = [
    "Det. R. Torres", "Off. M. Singh", "Det. K. Larson", "Sgt. P. Walsh",
    "Det. J. Holloway", "Off. C. Nguyen", "Det. B. Okafor", "Sgt. L. Petrov",
    "Off. T. Brennan", "Det. A. Ruiz", "Off. S. Yamamoto", "Det. H. Kowalski",
    "Sgt. D. Abramowitz", "Off. F. Martins", "Det. G. Reeves", "Sgt. N. Park",
]

# -------- tool/MO pools (hero is 8mm left-nick pry blade — use ONLY different ones) --------
RESIDENTIAL_MOS = [
    "forced a basement window using a flathead screwdriver (blade width ~12mm, no observable defects)",
    "pried the front door deadbolt housing with a crowbar, leaving wide 25mm spread marks",
    "removed a window AC unit to gain access through the resulting opening",
    "cut the screen on a first-floor window and lifted the unsecured sash",
    "used a bump key on the front door — no forced entry marks observed on the lock body",
    "broke a small pane of glass adjacent to the rear door deadbolt, reached in to unlock",
    "removed hinge pins from an outward-swinging back door",
    "used a hacksaw on a sliding door security bar; saw marks ~3mm blade width, coarse teeth",
    "gained entry through an unlocked garage side door",
    "exploited a malfunctioning latch on a rear French door — no tool marks",
    "pried a rear window frame with what appears to be a utility knife, 18mm blade impressions",
    "used a drill to defeat a deadbolt cylinder; drill bit diameter approx 9mm",
    "forced a garden-level window with a tire iron, producing 30mm wide pry impressions",
    "entered through a dog door after removing the flap mounting",
    "shimmed a door latch with a flexible tool (credit-card shimming), no structural damage",
    "forced a side-gate padlock with bolt cutters; clean shear marks on shackle",
    "used a pry bar with a distinctive curved tip; 20mm wide marks with right-side chip",
    "defeated a sliding door with a flat tool approximately 15mm wide, no defects noted",
    "unscrewed exposed hinges on rear deck door using a power drill",
    "broke the lock on a storm door then defeated the interior door with shoulder force",
]

CAR_THEFT_MOS = [
    "used a relay device to amplify key fob signal; no physical entry marks",
    "smashed the driver's-side window with a center-punch tool",
    "used a slim-jim style tool to unlock the door; minor scratch marks on door seal",
    "broke the steering column ignition — shattered plastic debris on seat",
    "towed the vehicle; no evidence of attempted forced entry",
    "used a key programmer to clone the OBD-II key profile",
    "broke the passenger window; glass safety gloves found at scene",
    "vehicle was taken while running (owner left engine on)",
]

VANDALISM_MOS = [
    "spray-painted graffiti on the front facade using multiple aerosol colors",
    "smashed storefront windows with a blunt instrument; glass pattern suggests heavy rock or hammer",
    "keyed multiple vehicles in the parking lot",
    "slashed two tires on each of four vehicles",
    "defaced a community mural with black spray paint",
    "broke exterior lighting fixtures; apparent deliberate targeting",
    "egged and toilet-papered the property",
    "tipped over the dumpster and scattered contents across the alley",
]

COMMERCIAL_MOS = [
    "shattered the glass front door using a large rock; alarm triggered within 30 seconds",
    "cut power to the building before entry; disabled the alarm panel",
    "entered through an unlocked roof hatch, bypassing ground-level security",
    "forced a rear service door with a crowbar (20mm wide blade marks, symmetrical)",
    "defeated a padlocked roll-up door with bolt cutters",
    "used a glass cutter on a display window, removed a 14-inch circular section",
    "forced a utility closet door to access interior alarm controls",
    "exploited a fire-exit crash bar from the exterior using a looped cord",
]

# -------- vehicle pools (hero is dark blue 2015-2018 Honda Accord — avoid that combo) --------
NOISE_VEHICLES = [
    "white Toyota Camry, late 2010s model, partial plate **7VX**",
    "silver Chevrolet Malibu, approximately 2019-2021, no plate observed",
    "red Ford F-150 pickup, older model, rusted wheel wells, plate **KMT 4**",
    "black Jeep Grand Cherokee, 2016-2018, tinted windows",
    "gray Nissan Altima, 2020-2022, small dent on rear bumper",
    "beige Honda CR-V, early 2010s, roof rack, partial plate **9AJ**",
    "dark green Subaru Outback, 2014-2017, bicycle rack mounted",
    "white cargo van, no side markings, ladder rack on roof",
    "orange Dodge Charger, late model, wide aftermarket rims",
    "tan Toyota 4Runner, 2012-2015, cracked rear light cluster",
    "blue Kia Sorento (light blue, not navy), 2018-2020, sunroof visible",
    "purple Hyundai Sonata, 2017-2019, rear spoiler",
    "brown Buick LeSabre, early 2000s, significant body rust",
    "maroon Chevrolet Suburban, 2010-2013, tow hitch",
    "yellow Volkswagen Golf, 2015-2018, stickers on rear window",
    "black Ford Escape, 2021-2022, chrome roof rails",
    "white Hyundai Tucson, 2019-2021, no distinguishing features",
    "dark gray Mazda CX-5, 2018-2020, missing front license plate",
    "metallic blue Ram 1500 (electric blue, not navy), 2020+, lifted suspension",
    "cream-colored Lexus ES, 2016-2019, dealer plate frame visible",
]

# -------- stolen item pools --------
RESIDENTIAL_ITEMS = [
    "two laptops, a television (55-inch), and approximately $400 cash",
    "jewelry valued at $2,800, a gaming console, and prescription medications",
    "power tools (circular saw, drill set) valued at $1,100",
    "bicycle (carbon fiber road bike, $3,200), camping gear",
    "firearms safe (contents unknown — homeowner declines to itemize)",
    "camera equipment valued at $2,600 and a tablet",
    "a watch collection, three rings, and $250 cash",
    "liquor ($180 value), electronics ($320), and kitchen appliances",
    "nothing taken — offender apparently disturbed by returning occupant",
    "collectible sports cards (approximate value $900), a gaming laptop",
    "holiday gifts, still wrapped — homeowner estimates $1,400 total",
    "artwork (two framed prints), vintage audio equipment",
    "child's piggy bank and a jar of loose change (~$60); nothing else",
]

COMMERCIAL_ITEMS = [
    "cash from two registers (approx. $1,200), a laptop, and a tablet used for POS",
    "pharmaceutical inventory (controlled substances — partial list forwarded to DEA)",
    "power tools on display (total approx. $4,800 retail)",
    "approximately $600 in currency and several gift cards",
    "high-end headphones and wireless speaker units (total approx. $3,100)",
    "copper wiring stripped from the utility room (~$700 scrap value)",
    "restaurant equipment: meat slicer, espresso machine ($2,400 combined)",
]

# -------- suspect descriptions --------
SUSPECT_DESCS = [
    "Male, 5'10\"-6'0\", heavy build, wearing dark hooded sweatshirt and jeans",
    "Male, approximately 5'8\", thin build, baseball cap, light-colored jacket",
    "Unknown — no witnesses; suspect avoided all camera angles",
    "Female, 5'5\"-5'7\", medium build, ponytail, yoga pants and athletic top",
    "Two males; descriptions vary — see individual witness statements",
    "Male, 6'2\"+, large frame, balaclava, dark work pants",
    "Not observed; entry and exit occurred during a period with no foot traffic",
    "Male, early 30s apparent age, short dark hair, clean-shaven, work boots",
    "Unknown number of suspects; evidence suggests more than one actor",
    "Male, approximately 40-50 years apparent age, gray beard, heavy winter coat",
]

def rand_date(year_min=2020, year_max=2025):
    year = random.randint(year_min, year_max)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{year}-{month:02d}-{day:02d}"

def rand_time():
    hour = random.randint(0, 23)
    minute = random.choice([0, 15, 30, 45])
    return f"{hour:02d}{minute:02d}"

def rand_address(city):
    num = random.randint(10, 999)
    street = random.choice(STREETS)
    return f"{num} {street}, {city}"

def incident_num(dept_abbr, year, n):
    return f"{dept_abbr}-{year}-{n:04d}"

def dept_abbr(dept):
    words = dept.replace(" Police Department", "").split()
    return "".join(w[0] for w in words).upper()

# -------- cross-reference pairs (noise files referencing each other) --------
# We'll assign some recurring MOs across noise incidents to simulate realistic
# cross-referencing (e.g. same MO seen in two different cities).
# These are DIFFERENT from the hero signature.

NOISE_MO_GROUPS = {
    "crowbar_wide": "pried the rear door with a crowbar, 25mm wide blade marks, no defects",
    "bump_key": "front door entry via bump key — no physical pry marks on the door frame",
    "drill_defeat": "drilled out the deadbolt cylinder (9mm bit), clean circular impression",
    "basement_window": "forced the basement window with a flathead screwdriver (12mm blade, no nicks)",
    "relay_fob": "vehicle taken via key-fob relay attack; no physical entry marks",
    "slimjim": "door unlocked using a slim-jim style tool; faint scratch marks on door weatherstrip",
}

# Map some incidents to a noise MO group to create cross-reference opportunities
CROSS_REF_ASSIGNMENTS = {}

def assign_cross_refs(total=250):
    """Pick ~60 incidents to share one of the noise MO groups."""
    groups = list(NOISE_MO_GROUPS.keys())
    for g in groups:
        count = random.randint(6, 12)
        chosen = random.sample(range(1, total + 1), count)
        for c in chosen:
            CROSS_REF_ASSIGNMENTS[c] = g

assign_cross_refs()

def generate_residential(idx, city, dept, date, num, officer):
    addr = rand_address(city)
    time = rand_time()
    items = random.choice(RESIDENTIAL_ITEMS)
    suspect = random.choice(SUSPECT_DESCS)
    vehicle = random.choice(NOISE_VEHICLES) if random.random() > 0.4 else None

    if idx in CROSS_REF_ASSIGNMENTS:
        group = CROSS_REF_ASSIGNMENTS[idx]
        mo = NOISE_MO_GROUPS[group]
        mo_note = f"\nINVESTIGATIVE NOTE: Entry method ('{group.replace('_',' ')}') matches reports filed in neighboring jurisdictions. Cross-reference with regional MO logs may be warranted.\n"
    else:
        mo = random.choice(RESIDENTIAL_MOS)
        mo_note = ""

    vehicle_line = f"\nVEHICLE OF INTEREST: A {vehicle} was observed near the scene within the offense window.\n" if vehicle else ""

    return f"""INCIDENT REPORT — {dept}
Date: {date}
Incident #: {num}
Type: Residential Burglary

Address: {addr}
Reporting Officer: {officer}
Time of Discovery: {time} hours (approx. offense window: prior overnight)

NARRATIVE:
Complainant reported a residential burglary upon returning home. Point of entry was established
as the {random.choice(['rear','side','front'])} of the residence. The offender {mo}.

ITEMS TAKEN: {items}

SUSPECT DESCRIPTION: {suspect}
{vehicle_line}{mo_note}
CANVASS: Door-to-door inquiries conducted in the surrounding block. {random.choice(['No additional witnesses identified.','One neighbor provided information — see attached statement.','Two neighbors reported hearing unusual sounds; statements pending.','No one reported seeing anything unusual.'])}

EVIDENCE COLLECTED: {random.choice(['No latent prints recovered. Photographed pry marks.','Partial shoe impression photographed on porch.','Glove smear on door handle — insufficient for comparison.','One partial latent print lifted from window sill; quality unknown.','No forensic evidence recovered.','Security footage from neighbor doorbell camera obtained; quality poor.'])}

CASE STATUS: {random.choice(['OPEN','OPEN','OPEN','SUSPENDED — no leads','OPEN — active follow-up'])}
"""

def generate_car_theft(idx, city, dept, date, num, officer):
    addr = rand_address(city)
    time = rand_time()
    mo = random.choice(CAR_THEFT_MOS)
    vehicle = random.choice(NOISE_VEHICLES)
    year_range = random.choice(["2018-2020", "2016-2019", "2019-2022", "2015-2018 (non-Accord)", "2012-2015"])
    make_model = random.choice(["Honda Civic", "Toyota RAV4", "Chevrolet Tahoe", "Ford Explorer",
                                 "Nissan Sentra", "Kia Optima", "Hyundai Elantra", "Subaru Forester",
                                 "Mazda3", "Volkswagen Jetta", "GMC Sierra", "Dodge Durango"])

    if idx in CROSS_REF_ASSIGNMENTS and CROSS_REF_ASSIGNMENTS[idx] in ("relay_fob", "slimjim"):
        mo = NOISE_MO_GROUPS[CROSS_REF_ASSIGNMENTS[idx]]

    return f"""INCIDENT REPORT — {dept}
Date: {date}
Incident #: {num}
Type: Motor Vehicle Theft

Address: {addr}
Reporting Officer: {officer}
Time of Complaint: {time} hours

NARRATIVE:
Owner reported vehicle stolen from {random.choice(['their driveway','the street in front of their residence','a public lot at the above address','a parking garage','the employer parking lot'])}.
Vehicle description: {year_range} {make_model}, {random.choice(['black','white','silver','gray','red','green','gold'])} in color.
Method: The offender {mo}.

SUSPECT VEHICLE SEEN LEAVING: {vehicle if random.random() > 0.5 else 'None reported'}

INVESTIGATIVE NOTE: {random.choice(['VIN submitted to NCIC.','Owner advised to contact insurance.','Partial plate circulated to patrol.','Recovered three days later, stripped, in an adjacent jurisdiction.','Vehicle recovered intact two blocks away — may be a joyriding incident.','No additional leads at this time.'])}

CASE STATUS: {random.choice(['OPEN','OPEN','SUSPENDED','VEHICLE RECOVERED — suspect unknown'])}
"""

def generate_vandalism(idx, city, dept, date, num, officer):
    addr = rand_address(city)
    time = rand_time()
    mo = random.choice(VANDALISM_MOS)
    damage_est = random.randint(200, 8000)

    return f"""INCIDENT REPORT — {dept}
Date: {date}
Incident #: {num}
Type: Vandalism / Malicious Mischief

Address: {addr}
Reporting Officer: {officer}
Time of Discovery: {time} hours

NARRATIVE:
Complainant reported vandalism to their property. The offender(s) {mo}.

ESTIMATED DAMAGE: ${damage_est:,}

SUSPECT DESCRIPTION: {random.choice(SUSPECT_DESCS)}

WITNESS ACCOUNTS: {random.choice(['No witnesses.','One witness — see attached.','Security camera captured partial image; face not visible.','Multiple witnesses; conflicting descriptions.'])}

PRIOR INCIDENTS: {random.choice(['No prior vandalism reported at this address.','Owner reports this is the second incident in six months.','Adjacent properties report similar vandalism — possible pattern.','No prior police contact at this location.'])}

CASE STATUS: {random.choice(['OPEN','SUSPENDED — no suspect identified','OPEN — review of area cameras requested'])}
"""

def generate_commercial(idx, city, dept, date, num, officer):
    addr = rand_address(city)
    time = rand_time()
    mo = random.choice(COMMERCIAL_MOS)
    items = random.choice(COMMERCIAL_ITEMS)
    suspect = random.choice(SUSPECT_DESCS)
    vehicle = random.choice(NOISE_VEHICLES) if random.random() > 0.3 else None

    if idx in CROSS_REF_ASSIGNMENTS:
        group = CROSS_REF_ASSIGNMENTS[idx]
        mo_note = f"\nINVESTIGATIVE NOTE: The MO is consistent with a series of commercial break-ins reported in {random.choice(CITIES)} over the past year. Cross-reference recommended.\n"
    else:
        mo_note = ""

    vehicle_line = f"\nVEHICLE OF INTEREST: Witness observed a {vehicle} in the alley behind the premises approximately 30 minutes before the alarm activation.\n" if vehicle else ""

    biz_type = random.choice(["convenience store", "electronics retailer", "pharmacy",
                               "restaurant", "hardware store", "clothing boutique",
                               "dental office", "auto parts store", "nail salon",
                               "pawn shop", "jewelry store", "sporting goods shop"])

    return f"""INCIDENT REPORT — {dept}
Date: {date}
Incident #: {num}
Type: Commercial Burglary

Address: {addr}  ({biz_type})
Reporting Officer: {officer}
Time of Alarm Activation / Discovery: {time} hours

NARRATIVE:
Officers responded to a commercial burglary at the above-listed {biz_type}. The offender(s) {mo}.

ITEMS TAKEN: {items}

SUSPECT DESCRIPTION: {suspect}
{vehicle_line}{mo_note}
ALARM RESPONSE TIME: {random.randint(4, 22)} minutes (alarm company notification to officer arrival).

EVIDENCE COLLECTED: {random.choice(['Interior security camera footage obtained — partially obscured.','No usable footage; cameras were offline.','Partial shoe impression near point of entry.','Fingerprint cards lifted from display case; analysis pending.','No forensic evidence collected.'])}

CASE STATUS: {random.choice(['OPEN','OPEN','SUSPENDED — no leads','OPEN — footage review ongoing'])}
"""

# -------- main generation loop --------

INCIDENT_TYPES = (
    ["residential"] * 150 +
    ["car_theft"] * 40 +
    ["vandalism"] * 30 +
    ["commercial"] * 30
)
random.shuffle(INCIDENT_TYPES)

total = 250
generated = 0

for i in range(1, total + 1):
    city_idx = (i - 1) % len(CITIES)
    city = CITIES[city_idx]
    dept = DEPARTMENTS[city_idx]
    abbr = dept_abbr(dept)
    date = rand_date()
    year = int(date.split("-")[0])
    num = incident_num(abbr, year, i)
    officer = random.choice(OFFICERS)

    inc_type = INCIDENT_TYPES[i - 1]

    if inc_type == "residential":
        content = generate_residential(i, city, dept, date, num, officer)
    elif inc_type == "car_theft":
        content = generate_car_theft(i, city, dept, date, num, officer)
    elif inc_type == "vandalism":
        content = generate_vandalism(i, city, dept, date, num, officer)
    else:
        content = generate_commercial(i, city, dept, date, num, officer)

    fname = RAW / f"incident_{i:03d}.txt"
    fname.write_text(content)
    generated += 1

print(f"Generated {generated} incident files in {RAW}")
