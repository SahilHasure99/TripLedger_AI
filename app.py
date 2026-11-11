import streamlit as st
import sys
import json
import html
from io import BytesIO
from pathlib import Path
from datetime import date, timedelta

# Ensure project root is on sys.path so agent/tool imports work
_PROJECT_DIR = Path(__file__).resolve().parent
if str(_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_DIR))

from agents.coordinator_agent import CoordinatorAgent
from utils.models import TripRequest
from utils.travel_features import (
    google_maps_search_url, google_hotel_photos_url, google_location_search_url,
    search_destination_catalog, trip_fingerprint, validate_trip, trip_to_dict,
    trip_to_text, budget_breakdown, trip_to_pdf, trip_to_docx,
    get_or_create_cached_plan,
)

# =========================================================
# CONFIGURATION
# =========================================================

PROJECT_DIR = Path(__file__).resolve().parent
MAIN_FILE = PROJECT_DIR / "main.py"

st.set_page_config(
    page_title="TravelMate | Explore Beyond",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui import tripledger_portal

# Session state initialization for workspace navigation
if "tl_workspace_nav" not in st.session_state:
    st.session_state["tl_workspace_nav"] = "TravelMate planner"

# ─── Master Sidebar Navigation ───
workspace_items = [
    ("🌍 TravelMate planner", "TravelMate planner"),
    ("📊 Overview", "Overview"),
    ("🧳 My trips", "My trips"),
    ("💳 Payments", "Payments"),
    ("📒 Transaction ledger", "Transaction ledger"),
    ("👤 Account & access", "Account & access"),
]

with st.sidebar:
    st.markdown("## ✦ TripLedger AI")
    st.markdown('<span class="tm-sticker"><i></i>LIVE WORKSPACE</span>', unsafe_allow_html=True)
    st.caption("Select a workspace view:")

    current_nav = st.session_state.get("tl_workspace_nav", "TravelMate planner")
    for label, target_key in workspace_items:
        is_selected = (current_nav == target_key)
        if st.button(
            label,
            key=f"side_btn_{target_key}",
            type="primary" if is_selected else "secondary",
            use_container_width=True
        ):
            st.session_state["tl_workspace_nav"] = target_key
            st.rerun()

    st.divider()
    if st.session_state.get("tl_access_token"):
        user_info = st.session_state.get("tl_user", {})
        st.success(f"Verified Session\n\n**{user_info.get('email', 'Traveller')}**")
    else:
        st.caption("Sign in to sync trips and payments")

# Real photography from Unsplash
HERO_IMAGE = (
    "https://images.unsplash.com/photo-1501785888041-af3ef285b470"
    "?auto=format&fit=crop&w=2200&q=85"
)

# ─── Destination data grouped by category ───

CATEGORIES = {
    "ISLAND ESCAPE": {
        "icon": "🏝️",
        "description": "Sun-kissed shores and turquoise waters await",
        "color": "#0ea5a0",
        "places": [
            {
                "name": "Bali, Indonesia",
                "description": "Tropical escapes & island sunsets among ancient temples and lush rice terraces.",
                "image": (
                    "https://images.unsplash.com/photo-1537996194471-e657df975ab4"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Temple Tours", "Rice Terraces", "Surfing", "Spa & Wellness"],
                "best_time": "April – October",
                "avg_budget": "₹45,000",
            },
            {
                "name": "Switzerland, Europe",
                "description": "Alpine escapes with snow-capped mountains, crystal-clear lakes, scenic trains, and charming villages.",
                "image": ("https://images.unsplash.com/photo-1531366936337-7c912a4589a7?auto=format&fit=crop&w=900&q=80"),
                "highlights": ["Swiss Alps", "Lake Cruises", "Scenic Train Rides", "Mountain Hiking"],
                "best_time": "June – September; December – March for snow",
                "avg_budget": "₹1,50,000"
            },
             {
                "name": "Japan",
                "description": "Cultural journeys blending ancient shrines, peaceful gardens, neon-lit cities, and breathtaking cherry blossoms.",
                "image": "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=900&q=80",
                "highlights": ["Mount Fuji", "Cherry Blossoms", "Temple Visits", "Traditional Cuisine"],
                "best_time": "March – May; October – November",
                "avg_budget": "₹1,00,000"
            },
             {
                "name": "Dubai, UAE",
                "description": "Modern city adventures featuring futuristic skyscrapers, golden deserts, luxury shopping, and vibrant nightlife.",
                "image": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=900&q=80",
                "highlights": ["Burj Khalifa", "Desert Safari", "Luxury Shopping", "Marina Cruises"],
                "best_time": "November – March",
                "avg_budget": "₹65,000"
            },
            {
                "name": "Maldives",
                "description": "Crystal-clear lagoons and overwater villas in a paradise archipelago.",
                "image": (
                    "https://images.unsplash.com/photo-1514282401047-d79a71a590e8"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Snorkeling", "Overwater Villas", "Sunset Cruises", "Diving"],
                "best_time": "November – April",
                "avg_budget": "₹1,20,000",
            },
             {
                "name": "Thailand",
                "description": "Tropical adventures with lively street markets, golden temples, tropical islands, and flavorful local cuisine.",
                "image": "https://images.unsplash.com/photo-1528181304800-259b08848526?auto=format&fit=crop&w=900&q=80",
                "highlights": ["Island Hopping", "Temple Tours", "Street Food", "Beach Adventures"],
                "best_time": "November – February",
                "avg_budget": "₹40,000"
            },
             {
                "name": "Paris, France",
                "description": "Romantic city escapes filled with iconic landmarks, charming cafés, world-class art, and elegant streets.",
                "image": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=900&q=80",
                "highlights": ["Eiffel Tower", "Louvre Museum", "Seine River Cruise", "French Cafés"],
                "best_time": "April – June; September – October",
                "avg_budget": "₹1,20,000"
            },
            {
                "name": "Singapore",
                "description": "A vibrant urban getaway with futuristic gardens, waterfront skylines, cultural neighborhoods, and exciting attractions.",
                "image": "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?auto=format&fit=crop&w=900&q=80",
                "highlights": ["Gardens by the Bay", "Marina Bay Sands", "Sentosa Island", "Night Safari"],
                "best_time": "February – April",
                "avg_budget": "₹55,000"
            },
             {
                "name": "New Zealand",
                "description": "Outdoor escapes across dramatic fjords, emerald lakes, snow-capped peaks, and rolling countryside.",
                "image": "https://images.unsplash.com/photo-1469521669194-babb45599def?auto=format&fit=crop&w=900&q=80",
                "highlights": ["Milford Sound", "Lake Tekapo", "Mountain Hiking", "Adventure Sports"],
                "best_time": "December – March",
                "avg_budget": "₹1,80,000"
            },
            {
                "name": "Iceland, Europe",
                "description": "Arctic escapes featuring powerful waterfalls, volcanic landscapes, glaciers, and magical Northern Lights.",
                "image": "https://images.unsplash.com/photo-1476610182048-b716b8518aae?auto=format&fit=crop&w=900&q=80",
                "highlights": ["Northern Lights", "Glacier Adventures", "Waterfall Tours", "Geothermal Spas"],
                "best_time": "June – August; September – March for Northern Lights",
                "avg_budget": "₹1,50,000"
            },
            {
                "name": "Phuket, Thailand",
                "description": "Vibrant nightlife, stunning beaches and rich Thai culture.",
                "image": (
                    "https://images.unsplash.com/photo-1589394815804-964ed0be2eb5"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Beach Hopping", "Thai Cuisine", "Island Tours", "Night Markets"],
                "best_time": "November – February",
                "avg_budget": "₹35,000",
            },
        ],
    },
    "MOUNTAIN RETREAT": {
        "icon": "🏔️",
        "description": "Majestic peaks and crisp alpine air",
        "color": "#2d6a4f",
        "places": [
            {
                "name": "Swiss Alps",
                "description": "Mountain air & scenic adventures among snow-capped peaks and charming villages.",
                "image": (
                    "https://images.unsplash.com/photo-1531366936337-7c912a4589a7"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Skiing", "Hiking", "Scenic Trains", "Cheese & Chocolate Tours"],
                "best_time": "June – September / December – March",
                "avg_budget": "₹1,50,000",
            },
            {
                "name": "Manali, India",
                "description": "Snow-dusted valleys with adventure sports and serene mountain temples.",
                "image": (
                    "https://images.unsplash.com/photo-1626621341517-bbf3d9990a23"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Paragliding", "Rohtang Pass", "Old Manali", "River Rafting"],
                "best_time": "October – February / March – June",
                "avg_budget": "₹15,000",
            },
                        
            {
                "name": "Dolomites, Italy",
                "description": "Dramatic limestone peaks, alpine meadows, and peaceful mountain villages with breathtaking hiking trails.",
                "image": (
                    "https://images.unsplash.com/photo-1519681393784-d120267933ba"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Mountain Hiking", "Alpine Lakes", "Cable Cars", "Scenic Villages"],
                "best_time": "June – September / December – March",
                "avg_budget": "₹1,20,000",
            },
            {
                "name": "Sikkim, India",
                "description": "A peaceful Himalayan escape with snow-covered peaks, Buddhist monasteries, and spectacular mountain valleys.",
                "image": (
                    "https://images.unsplash.com/photo-1622308644420-b20142dc993c"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Kanchenjunga Views", "Monastery Tours", "Tsomgo Lake", "Mountain Drives"],
                "best_time": "March – May / October – November",
                "avg_budget": "₹20,000",
            },
            {
                "name": "Banff, Canada",
                "description": "A breathtaking mountain retreat with turquoise alpine lakes, towering peaks, evergreen forests, and cozy lodges.",
                "image": (
                    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQgEdcNinz2g0GpgPCT2x-XZp3mmHSbg1a-w2cWdCrMKg&s=10"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Lake Louise", "Mountain Hiking", "Wildlife Watching", "Gondola Rides"],
                "best_time": "June – September / December – March",
                "avg_budget": "₹1,80,000",
            },
            {
                "name": "Swiss Jura, Switzerland",
                "description": "Quiet mountain escapes with forested ridges, rolling green hills, and charming countryside villages.",
                "image": (
                    "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Forest Hiking", "Mountain Views", "Village Stays", "Nature Trails"],
                "best_time": "May – October",
                "avg_budget": "₹1,30,000",
            },
            {
                "name": "Gulmarg, India",
                "description": "A Himalayan paradise with snowy slopes, pine forests, alpine meadows, and spectacular mountain scenery.",
                "image": (
                    "https://images.unsplash.com/photo-1605649487212-47bdab064df7"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Gondola Rides", "Skiing", "Snowboarding", "Alpine Meadows"],
                "best_time": "December – March / May – September",
                "avg_budget": "₹18,000",
            },
            {
                "name": "Zermatt, Switzerland",
                "description": "An elegant alpine retreat beneath the iconic Matterhorn, featuring mountain railways and peaceful car-free streets.",
                "image": (
                    "https://images.unsplash.com/photo-1531366936337-7c912a4589a7"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Matterhorn Views", "Gornergrat Railway", "Skiing", "Alpine Hiking"],
                "best_time": "June – September / December – March",
                "avg_budget": "₹1,60,000",
            },
            {
                "name": "Queenstown, New Zealand",
                "description": "A scenic lakeside mountain getaway surrounded by dramatic peaks, vineyards, and adventure-filled valleys.",
                "image": (
                    "https://images.unsplash.com/photo-1469521669194-babb45599def"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Lake Wakatipu", "Mountain Gondola", "Hiking", "Adventure Sports"],
                "best_time": "December – February / June – August",
                "avg_budget": "₹1,70,000",
            },
            {
                "name": "Leh-Ladakh, India",
                "description": "A high-altitude Himalayan escape with rugged mountains, ancient monasteries, crystal-blue lakes, and winding roads.",
                "image": (
                    "https://images.unsplash.com/photo-1519681393784-d120267933ba"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Pangong Lake", "Nubra Valley", "Monastery Visits", "Mountain Road Trips"],
                "best_time": "May – September",
                "avg_budget": "₹25,000",
            },
            {
                "name": "Chamonix, France",
                "description": "A classic alpine retreat beneath Mont Blanc, with glacier panoramas, mountain cable cars, and picturesque chalets.",
                "image": (
                    "https://images.unsplash.com/photo-1506905925346-21bda4d32df4"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Mont Blanc Views", "Glacier Excursions", "Cable Cars", "Alpine Hiking"],
                "best_time": "June – September / December – March",
                "avg_budget": "₹1,40,000",
            },


            {
                "name": "Patagonia, Argentina",
                "description": "Untamed wilderness of glaciers, forests, and turquoise lakes.",
                "image": (
                    "https://images.unsplash.com/photo-1531761535209-180857e963b9"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Glacier Trekking", "Torres del Paine", "Wildlife", "Kayaking"],
                "best_time": "October – March",
                "avg_budget": "₹2,00,000",
            },
        ]
    },
    "COASTAL GETAWAY": {
        "icon": "🌊",
        "description": "Where the ocean meets unforgettable moments",
        "color": "#3a86c4",
        "places": [
            {
                "name": "Santorini, Greece",
                "description": "Whitewashed beauty by the Aegean Sea with legendary sunsets.",
                "image": (
                    "https://images.unsplash.com/photo-1613395877344-13d4a8e0d49e"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Oia Sunset", "Wine Tasting", "Caldera Cruise", "Greek Cuisine"],
                "best_time": "April – October",
                "avg_budget": "₹1,00,000",
            },
             {
                "name": "Langkawi, Malaysia",
                "description": "A tropical island escape with emerald rainforests, turquoise bays, sandy beaches, and spectacular coastal views.",
                "image": (
                    "https://images.unsplash.com/photo-1501785888041-af3ef285b470"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Island Hopping", "Sky Bridge", "Mangrove Tours", "Beach Sunsets"],
                "best_time": "November – April",
                "avg_budget": "₹45,000",
            },
            {
                "name": "Krabi, Thailand",
                "description": "A stunning seaside retreat featuring limestone cliffs, hidden lagoons, tropical beaches, and clear blue waters.",
                "image": (
                    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Railay Beach", "Four Islands Tour", "Kayaking", "Snorkeling"],
                "best_time": "November – April",
                "avg_budget": "₹40,000",
            },
            {
                "name": "Mauritius",
                "description": "A beautiful Indian Ocean escape with coral reefs, volcanic scenery, palm-lined shores, and peaceful lagoons.",
                "image": (
                    "https://images.unsplash.com/photo-1519046904884-53103b34b206"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Catamaran Cruises", "Coral Reef Diving", "Chamarel", "Beach Resorts"],
                "best_time": "May – December",
                "avg_budget": "₹85,000",
            },
            {
                "name": "Zanzibar, Tanzania",
                "description": "An exotic coastal escape blending white-sand beaches, turquoise waters, spice plantations, and historic island culture.",
                "image": (
                    "https://images.unsplash.com/photo-1544551763-46a013bb70d5"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Stone Town", "Dhow Sailing", "Snorkeling", "Spice Tours"],
                "best_time": "June – October / December – February",
                "avg_budget": "₹90,000",
            },
            {
                "name": "Algarve, Portugal",
                "description": "A sun-soaked European coastline with golden cliffs, sea caves, charming fishing towns, and hidden sandy coves.",
                "image": (
                    "https://images.unsplash.com/photo-1510414842594-a61c69b5ae57"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Benagil Cave", "Coastal Hiking", "Boat Tours", "Seafood Dining"],
                "best_time": "May – September",
                "avg_budget": "₹1,10,000",
            },
            {
                "name": "Pondicherry, India",
                "description": "A charming seaside getaway with French colonial streets, colorful cafés, tranquil promenades, and coastal sunsets.",
                "image": (
                    "https://images.unsplash.com/photo-1473116763249-2faaef81ccda"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Promenade Beach", "French Quarter", "Auroville", "Café Hopping"],
                "best_time": "October – March",
                "avg_budget": "₹12,000",
            },
            {
                "name": "Palawan, Philippines",
                "description": "A tropical paradise of dramatic limestone islands, hidden lagoons, turquoise seas, and pristine white beaches.",
                "image": (
                    "https://images.unsplash.com/photo-1518509562904-e7ef99cdcc86"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["El Nido Lagoons", "Island Hopping", "Kayaking", "Coral Reefs"],
                "best_time": "November – May",
                "avg_budget": "₹75,000",
            },
            {
                "name": "Kovalam, India",
                "description": "A relaxing beach destination with crescent-shaped shores, swaying palms, lighthouse views, and traditional wellness retreats.",
                "image": (
                    "https://images.unsplash.com/photo-1500375592092-40eb2168fd21"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Lighthouse Beach", "Ayurvedic Spas", "Surfing", "Seafood"],
                "best_time": "November – February",
                "avg_budget": "₹15,000",
            },
            {
                "name": "Goa, India",
                "description": "Golden beaches, vibrant nightlife and Portuguese-era charm.",
                "image": (
                    "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Beach Parties", "Water Sports", "Old Goa Churches", "Seafood"],
                "best_time": "November – February",
                "avg_budget": "₹12,000",
            },
            {
                "name": "Amalfi Coast, Italy",
                "description": "Dramatic cliffs, pastel villages and Mediterranean glamour.",
                "image": (
                    "https://images.unsplash.com/photo-1534308983496-4fabb1a015ee"
                    "?auto=format&fit=crop&w=900&q=80"
                ),
                "highlights": ["Positano Walk", "Limoncello Tasting", "Boat Tours", "Ravello Gardens"],
                "best_time": "May – September",
                "avg_budget": "₹1,30,000",
            },
        ],
    },
}

# ─── Session state defaults ───

if "page" not in st.session_state:
    st.session_state["page"] = "home"
if "selected_category" not in st.session_state:
    st.session_state["selected_category"] = None
if "selected_place" not in st.session_state:
    st.session_state["selected_place"] = None
if "custom_destination" not in st.session_state:
    st.session_state["custom_destination"] = None


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown(
    """
    <style>
    @import url(
      'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@500;600;700&display=swap'
    );

    :root {
        --ink: #142d29;
        --green: #1f5748;
        --mint: #e9f2e9;
        --paper: #faf9f5;
        --muted: #718078;
        --gold: #d7aa65;
    }

    html {
        scroll-behavior: smooth;
    }

    .stApp {
        background: var(--paper);
        color: var(--ink);
        font-family: 'DM Sans', sans-serif;
    }

    #MainMenu, footer, header {
        visibility: hidden;
    }

    .block-container {
        max-width: 1320px;
        padding: 1.4rem 2.2rem 4rem;
    }

    /* Navigation */

    .nav {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0 24px;
        animation: fadeDown 0.8s ease both;
    }

    .brand {
        font-size: 25px;
        font-weight: 700;
        letter-spacing: -1px;
        color: var(--ink);
    }

    .brand span {
        color: var(--green);
    }

    .nav-label {
        color: #65736a;
        font-size: 13px;
        letter-spacing: 2px;
        text-transform: uppercase;
    }

    /* Hero */

    .hero {
        position: relative;
        overflow: hidden;
        min-height: 470px;
        border-radius: 25px;
        background-image:
            linear-gradient(
                90deg,
                rgba(10, 31, 28, 0.79) 0%,
                rgba(10, 31, 28, 0.48) 46%,
                rgba(10, 31, 28, 0.06) 100%
            ),
            url("HERO_REPLACE");
        background-size: cover;
        background-position: center;
        display: flex;
        align-items: center;
        padding: 50px;
        animation: heroReveal 1s ease both;
        box-shadow: 0 18px 55px rgba(26, 53, 43, 0.12);
    }

    .hero-content {
        max-width: 640px;
        animation: fadeUp 1s 0.2s ease both;
    }

    .eyebrow {
        display: inline-block;
        color: #fff1cf;
        border: 1px solid rgba(255,255,255,0.45);
        background: rgba(255,255,255,0.10);
        padding: 9px 15px;
        border-radius: 30px;
        font-size: 11px;
        letter-spacing: 2px;
        margin-bottom: 23px;
        backdrop-filter: blur(8px);
    }

    .hero h1 {
        font-family: 'Playfair Display', serif;
        font-size: clamp(42px, 5vw, 70px);
        line-height: 1.09;
        letter-spacing: -1.5px;
        color: white;
        margin: 0 0 20px;
        font-weight: 600;
    }

    .hero h1 em {
        color: #e9c78e;
        font-style: normal;
    }

    .hero p {
        color: rgba(255,255,255,0.88);
        font-size: 16px;
        line-height: 1.8;
        max-width: 470px;
        margin-bottom: 25px;
    }

    .hero-pill {
        display: inline-block;
        background: #fff;
        color: var(--ink);
        padding: 13px 19px;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 700;
    }

    /* Section headings */

    .section {
        padding-top: 45px;
        animation: fadeUp 0.8s ease both;
    }

    .section-kicker {
        color: var(--green);
        font-size: 11px;
        letter-spacing: 2.5px;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    .section-title {
        font-family: 'Playfair Display', serif;
        font-size: 35px;
        line-height: 1.2;
        color: var(--ink);
        margin: 0 0 10px;
    }

    .section-desc {
        font-size: 14px;
        line-height: 1.8;
        color: var(--muted);
        margin-bottom: 22px;
    }

    /* Destination cards */

    .destination-card {
        position: relative;
        height: 250px;
        overflow: hidden;
        border-radius: 17px;
        background: #dce6dc;
        background-size: cover;
        background-position: center;
        margin-bottom: 8px;
        transition: transform 0.35s ease, box-shadow 0.35s ease;
        cursor: pointer;
    }

    .destination-card:hover {
        transform: translateY(-7px);
        box-shadow: 0 18px 35px rgba(20,45,41,0.18);
    }

    .destination-overlay {
        position: absolute;
        inset: 0;
        background: linear-gradient(
            180deg,
            transparent 25%,
            rgba(8,26,22,0.85) 100%
        );
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        padding: 22px;
    }

    .destination-tag {
        color: #f4d9a8;
        font-size: 10px;
        letter-spacing: 2px;
        font-weight: 700;
        margin-bottom: 9px;
    }

    .destination-name {
        color: white;
        font-family: 'Playfair Display', serif;
        font-size: 25px;
        margin-bottom: 5px;
    }

    .destination-desc {
        color: rgba(255,255,255,0.85);
        font-size: 12px;
    }

    /* Category tabs */

    .category-tab {
        background: white;
        border: 1.5px solid #e3e7df;
        border-radius: 16px;
        padding: 22px 20px;
        text-align: center;
        transition: all 0.3s ease;
        cursor: pointer;
        min-height: 130px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 6px;
    }

    .category-tab:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 30px rgba(20,45,41,0.12);
        border-color: var(--green);
    }

    .category-tab .cat-icon {
        font-size: 36px;
        margin-bottom: 4px;
    }

    .category-tab .cat-title {
        font-size: 14px;
        font-weight: 700;
        color: var(--ink);
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }

    .category-tab .cat-desc {
        font-size: 11px;
        color: var(--muted);
        line-height: 1.5;
    }

    /* Place detail hero */

    .place-hero {
        position: relative;
        overflow: hidden;
        min-height: 340px;
        border-radius: 22px;
        background-size: cover;
        background-position: center;
        display: flex;
        align-items: flex-end;
        padding: 35px;
        box-shadow: 0 18px 45px rgba(26, 53, 43, 0.14);
        animation: heroReveal 0.8s ease both;
    }

    .place-hero-overlay {
        position: absolute;
        inset: 0;
        background: linear-gradient(
            180deg,
            transparent 30%,
            rgba(8, 26, 22, 0.88) 100%
        );
    }

    .place-hero-content {
        position: relative;
        z-index: 1;
    }

    .place-hero-content h1 {
        font-family: 'Playfair Display', serif;
        font-size: 44px;
        color: white;
        margin: 0 0 8px;
        font-weight: 600;
    }

    .place-hero-content p {
        color: rgba(255,255,255,0.9);
        font-size: 15px;
        line-height: 1.7;
        max-width: 550px;
    }

    /* Highlight chips */

    .highlight-chip {
        display: inline-block;
        background: var(--mint);
        color: var(--green);
        padding: 8px 16px;
        border-radius: 25px;
        font-size: 12px;
        font-weight: 600;
        margin: 4px 4px 4px 0;
        letter-spacing: 0.5px;
    }

    /* Info cards */

    .info-card {
        background: white;
        border: 1px solid #e8ebe4;
        border-radius: 14px;
        padding: 20px;
        text-align: center;
    }

    .info-card .info-label {
        font-size: 11px;
        color: var(--muted);
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 6px;
    }

    .info-card .info-value {
        font-family: 'Playfair Display', serif;
        font-size: 20px;
        color: var(--ink);
        font-weight: 600;
    }

    /* Breadcrumb */

    .breadcrumb {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        color: var(--muted);
        margin-bottom: 20px;
        animation: fadeDown 0.6s ease both;
    }

    .breadcrumb .sep {
        color: #c5cec6;
    }

    .breadcrumb .current {
        color: var(--ink);
        font-weight: 600;
    }

    /* Form */

    .form-panel {
        background: #ffffff;
        padding: 24px;
        border: 1px solid #e8ebe4;
        border-radius: 18px;
        box-shadow: 0 12px 35px rgba(27, 54, 44, 0.04);
    }

    .form-caption {
        color: var(--muted);
        font-size: 13px;
        line-height: 1.7;
        margin-bottom: 15px;
    }

    .stTextInput label,
    .stNumberInput label,
    .stDateInput label,
    .stMultiSelect label {
        color: var(--ink) !important;
        font-weight: 600 !important;
        font-size: 13px !important;
    }

    .stTextInput input,
    .stNumberInput input,
    .stDateInput input {
        border-radius: 10px !important;
        background: #fcfcfa !important;
    }

    .stTextInput input:focus,
    .stNumberInput input:focus {
        border-color: var(--green) !important;
        box-shadow: 0 0 0 2px rgba(31,87,72,0.08) !important;
    }

    div[data-baseweb="select"] > div {
        border-radius: 10px;
    }

    div.stButton > button,
    div.stFormSubmitButton > button {
        background: var(--green) !important;
        color: white !important;
        border: 1px solid var(--green) !important;
        border-radius: 11px !important;
        min-height: 48px;
        font-weight: 700 !important;
        transition: all 0.25s ease;
    }

    div.stButton > button:hover,
    div.stFormSubmitButton > button:hover {
        background: #143e32 !important;
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(31,87,72,0.18);
    }

    /* Feature strip */

    .feature {
        background: var(--mint);
        border-radius: 14px;
        padding: 19px 15px;
        margin-top: 14px;
        min-height: 95px;
    }

    .feature-icon {
        font-size: 23px;
        margin-bottom: 9px;
    }

    .feature-title {
        font-size: 13px;
        font-weight: 700;
        color: var(--ink);
        margin-bottom: 5px;
    }

    .feature-desc {
        font-size: 11px;
        line-height: 1.6;
        color: #66796c;
    }

    .result-panel {
        background: #ffffff;
        border: 1px solid #e8ebe4;
        padding: 23px;
        border-radius: 15px;
        margin: 15px 0;
    }

    /* ─── Professional Trip Plan Output ─── */

    .trip-header {
        background: linear-gradient(135deg, #142d29 0%, #1f5748 50%, #2d6a4f 100%);
        border-radius: 20px;
        padding: 35px 40px;
        color: white;
        margin-bottom: 25px;
        position: relative;
        overflow: hidden;
        animation: fadeUp 0.6s ease both;
    }

    .trip-header::before {
        content: '';
        position: absolute;
        top: -40px; right: -40px;
        width: 200px; height: 200px;
        background: rgba(255,255,255,0.04);
        border-radius: 50%;
    }

    .trip-header::after {
        content: '';
        position: absolute;
        bottom: -60px; left: 30%;
        width: 300px; height: 300px;
        background: rgba(255,255,255,0.02);
        border-radius: 50%;
    }

    .trip-header .trip-route {
        font-family: 'Playfair Display', serif;
        font-size: 32px;
        font-weight: 600;
        margin-bottom: 4px;
    }

    .trip-header .trip-dates {
        font-size: 14px;
        color: rgba(255,255,255,0.75);
        margin-bottom: 16px;
    }

    .trip-header .trip-stats {
        display: flex;
        gap: 30px;
        flex-wrap: wrap;
    }

    .trip-header .trip-stat {
        text-align: center;
    }

    .trip-header .trip-stat .stat-value {
        font-size: 22px;
        font-weight: 700;
        color: #e9c78e;
    }

    .trip-header .trip-stat .stat-label {
        font-size: 10px;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: rgba(255,255,255,0.6);
        margin-top: 2px;
    }

    /* Section dividers inside results */

    .plan-section-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 30px 0 16px;
        animation: fadeUp 0.5s ease both;
    }

    .plan-section-header .ps-icon {
        font-size: 24px;
    }

    .plan-section-header .ps-title {
        font-family: 'Playfair Display', serif;
        font-size: 22px;
        color: var(--ink);
        font-weight: 600;
    }

    .plan-section-header .ps-line {
        flex: 1;
        height: 1px;
        background: #e0e5dc;
        margin-left: 8px;
    }

    /* Flight cards */

    .flight-card {
        background: white;
        border: 1px solid #e8ebe4;
        border-radius: 16px;
        padding: 20px 22px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: all 0.3s ease;
        animation: fadeUp 0.5s ease both;
    }

    .flight-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 28px rgba(20,45,41,0.1);
        border-color: var(--green);
    }

    .flight-card .fc-airline {
        font-weight: 700;
        font-size: 15px;
        color: var(--ink);
    }

    .flight-card .fc-route {
        font-size: 12px;
        color: var(--muted);
        margin-top: 3px;
    }

    .flight-card .fc-duration {
        background: var(--mint);
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        color: var(--green);
    }

    .flight-card .fc-price {
        font-family: 'Playfair Display', serif;
        font-size: 22px;
        font-weight: 700;
        color: var(--green);
    }

    .flight-card .fc-badge {
        display: inline-block;
        background: #d7aa65;
        color: white;
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 1px;
        padding: 3px 10px;
        border-radius: 12px;
        margin-left: 6px;
        text-transform: uppercase;
        vertical-align: middle;
    }

    /* Hotel cards */

    .hotel-card {
        background: white;
        border: 1px solid #e8ebe4;
        border-radius: 16px;
        padding: 22px;
        margin-bottom: 12px;
        transition: all 0.3s ease;
        animation: fadeUp 0.5s ease both;
    }

    .hotel-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 28px rgba(20,45,41,0.1);
        border-color: var(--green);
    }

    .hotel-card .hc-top {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 10px;
    }

    .hotel-card .hc-name {
        font-weight: 700;
        font-size: 16px;
        color: var(--ink);
    }

    .hotel-card .hc-rating {
        background: var(--green);
        color: white;
        padding: 4px 12px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 700;
    }

    .hotel-card .hc-neighborhood {
        font-size: 12px;
        color: var(--muted);
        margin-bottom: 8px;
    }

    .hotel-card .hc-price {
        font-family: 'Playfair Display', serif;
        font-size: 20px;
        font-weight: 700;
        color: var(--green);
    }

    .hotel-card .hc-price span {
        font-family: 'DM Sans', sans-serif;
        font-size: 12px;
        font-weight: 400;
        color: var(--muted);
    }

    /* Weather cards */

    .weather-row {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin-bottom: 10px;
    }

    .weather-card {
        flex: 1;
        min-width: 140px;
        background: white;
        border: 1px solid #e8ebe4;
        border-radius: 16px;
        padding: 18px;
        text-align: center;
        transition: all 0.3s ease;
        animation: fadeUp 0.5s ease both;
    }

    .weather-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 22px rgba(20,45,41,0.08);
    }

    .weather-card .wc-day {
        font-size: 11px;
        color: var(--muted);
        letter-spacing: 1px;
        text-transform: uppercase;
        font-weight: 600;
        margin-bottom: 8px;
    }

    .weather-card .wc-icon {
        font-size: 32px;
        margin-bottom: 6px;
    }

    .weather-card .wc-summary {
        font-size: 13px;
        font-weight: 600;
        color: var(--ink);
        margin-bottom: 6px;
    }

    .weather-card .wc-temps {
        font-size: 12px;
        color: var(--muted);
    }

    .weather-card .wc-temps strong {
        color: var(--ink);
        font-size: 16px;
    }

    /* Itinerary timeline */

    .itinerary-day {
        position: relative;
        padding: 0 0 25px 35px;
        border-left: 2px solid #d6ddd8;
        margin-left: 12px;
        animation: fadeUp 0.5s ease both;
    }

    .itinerary-day:last-child {
        border-left: 2px solid transparent;
    }

    .itinerary-day::before {
        content: '';
        position: absolute;
        left: -8px; top: 3px;
        width: 14px; height: 14px;
        border-radius: 50%;
        background: var(--green);
        border: 3px solid var(--paper);
        box-shadow: 0 0 0 2px var(--green);
    }

    .itinerary-day .id-label {
        font-weight: 700;
        font-size: 14px;
        color: var(--green);
        margin-bottom: 3px;
    }

    .itinerary-day .id-date {
        font-size: 11px;
        color: var(--muted);
        margin-bottom: 10px;
    }

    .itinerary-day .id-activity {
        background: white;
        border: 1px solid #eaede7;
        border-radius: 10px;
        padding: 10px 15px;
        font-size: 13px;
        color: var(--ink);
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 8px;
        transition: all 0.2s ease;
    }

    .itinerary-day .id-activity:hover {
        background: var(--mint);
        border-color: var(--green);
    }

    .itinerary-day .id-activity .act-dot {
        width: 6px; height: 6px;
        border-radius: 50%;
        background: var(--gold);
        flex-shrink: 0;
    }

    /* Trip summary footer */

    .trip-footer {
        background: linear-gradient(135deg, #f5f0e8 0%, #e9f2e9 100%);
        border-radius: 16px;
        padding: 25px 30px;
        margin-top: 20px;
        text-align: center;
        animation: fadeUp 0.6s ease both;
    }

    .trip-footer .tf-text {
        font-family: 'Playfair Display', serif;
        font-size: 20px;
        color: var(--ink);
        margin-bottom: 6px;
    }

    .trip-footer .tf-sub {
        font-size: 13px;
        color: var(--muted);
    }

    .footer {
        border-top: 1px solid #e3e7df;
        margin-top: 55px;
        padding-top: 25px;
        color: #78837b;
        font-size: 12px;
        text-align: center;
        line-height: 1.9;
    }

    /* Back button styling */
    .back-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: transparent;
        border: 1.5px solid #d0d7d1;
        color: var(--ink);
        padding: 8px 18px;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.25s ease;
        font-family: 'DM Sans', sans-serif;
        margin-bottom: 18px;
    }

    .back-btn:hover {
        border-color: var(--green);
        color: var(--green);
        background: var(--mint);
    }

    /* Animations */

    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(22px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes fadeDown {
        from { opacity: 0; transform: translateY(-12px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes heroReveal {
        from { opacity: 0; transform: scale(0.985); }
        to { opacity: 1; transform: scale(1); }
    }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: 0.01ms !important;
            transition-duration: 0.01ms !important;
            scroll-behavior: auto !important;
        }
    }

    @media (max-width: 700px) {
        .block-container {
            padding: 1rem 1rem 3rem;
        }

        .hero {
            min-height: 420px;
            padding: 27px;
            border-radius: 18px;
        }

        .hero h1 {
            font-size: 43px;
        }

        .section-title {
            font-size: 29px;
        }

        .nav-label {
            font-size: 9px;
            letter-spacing: 1px;
        }
    }
    /* Additive motion polish: original TravelMate palette and layout remain unchanged. */
    @keyframes tmSoftGlow {
        0%, 100% { box-shadow: 0 8px 24px rgba(31,87,72,0.05); }
        50% { box-shadow: 0 12px 32px rgba(31,87,72,0.12); }
    }
    .hotel-card, .flight-card, .weather-card, .itinerary-day {
        will-change: transform;
    }
    .hotel-card:hover, .flight-card:hover, .weather-card:hover {
        transform: translateY(-4px) scale(1.005);
    }
    .travelmate-feature-note {
        border-left: 3px solid var(--gold);
        background: linear-gradient(110deg, rgba(233,242,233,.8), rgba(250,249,245,.7));
        border-radius: 0 12px 12px 0;
        padding: 12px 15px;
        margin: 12px 0 18px;
        animation: fadeUp .45s ease both;
    }
    .hotel-link-caption { color: var(--muted); font-size: 11px; margin-top: -5px; }

    /* Additive destination search: original TravelMate palette and typography retained. */
    .tm-search-panel {
        position: relative; overflow: hidden; display: grid;
        grid-template-columns: minmax(0, 1fr) 120px; gap: 14px; align-items: center;
        margin: 20px 0 26px; padding: 22px 24px;
        border: 1px solid rgba(31,87,72,.15); border-radius: 22px;
        background: linear-gradient(115deg, rgba(255,255,255,.98), rgba(233,242,233,.88));
        box-shadow: 0 12px 35px rgba(20,45,41,.07);
        animation: searchPanelIn .65s cubic-bezier(.2,.7,.2,1) both;
    }
    .tm-search-panel:before { content:""; position:absolute; width:210px; height:210px; right:70px; top:-140px;
        border-radius:50%; background:rgba(215,170,101,.13); pointer-events:none; }
    .tm-search-kicker { color:var(--green); font-size:11px; font-weight:800; letter-spacing:2px; text-transform:uppercase; }
    .tm-search-title { color:var(--ink); font-family:'Playfair Display',serif; font-size:clamp(22px,3vw,31px); line-height:1.15; margin:6px 0; }
    .tm-search-copy { color:var(--muted); font-size:13px; margin:0 0 12px; }
    .tm-search-character { width:128px; height:auto; max-width:100%; justify-self:center; overflow:visible;
        filter:drop-shadow(0 12px 12px rgba(31,87,72,.16)); transform-origin:50% 85%;
        animation:animeFloat 3.6s ease-in-out infinite; transition:filter .35s, transform .35s; }
    .tm-anime-hair { transform-box:fill-box; transform-origin:50% 15%; animation:hairSway 3.8s ease-in-out infinite; }
    .tm-anime-blink { transform-box:fill-box; transform-origin:center; animation:animeBlink 4.8s infinite; }
    .tm-anime-star { transform-box:fill-box; transform-origin:center; animation:starTwinkle 2.1s ease-in-out infinite; }
    .tm-search-panel:after { content:"✦"; position:absolute; right:28px; bottom:18px; color:#d7aa65;
        font-size:19px; opacity:.7; animation:starDrift 3s ease-in-out infinite; pointer-events:none; }
    body:has(.st-key-location_search_input input:focus) .tm-search-character,
    body:has(.st-key-location_search_submit button:hover) .tm-search-character { animation:animeExcited .8s ease-in-out infinite; filter:drop-shadow(0 14px 14px rgba(31,87,72,.22)); }
    .tm-search-tip { color:var(--muted); font-size:11px; margin-top:6px; }
    .tm-operation-card { display:flex; align-items:center; gap:16px; margin:8px 0 16px; padding:12px 18px;
        border:1px solid rgba(31,87,72,.14); border-radius:18px;
        background:linear-gradient(105deg,rgba(233,242,233,.92),rgba(255,255,255,.96));
        box-shadow:0 10px 26px rgba(31,87,72,.08); animation:searchPanelIn .35s ease both; }
    .tm-operation-girl { width:80px; height:80px; flex:0 0 80px; overflow:visible;
        filter:drop-shadow(0 7px 8px rgba(31,87,72,.15)); animation:animeExcited .72s ease-in-out infinite; }
    .tm-operation-title { color:var(--green); font-size:15px; font-weight:800; margin-bottom:3px; }
    .tm-operation-copy { color:var(--muted); font-size:12px; margin:0; }
    .tm-operation-dots:after { content:""; display:inline-block; width:1.5em; text-align:left; animation:loadingDots 1.2s steps(4,end) infinite; }
    .st-key-location_search_input input { border-radius:14px !important; min-height:48px; border-color:rgba(31,87,72,.28) !important; }
    .st-key-location_search_input input:focus { border-color:var(--green) !important; box-shadow:0 0 0 3px rgba(31,87,72,.10) !important; }
    @keyframes searchPanelIn { from {opacity:0; transform:translateY(12px)} to {opacity:1; transform:translateY(0)} }
    @keyframes animeFloat { 0%,100% { transform:translateY(0) rotate(-1deg) } 50% { transform:translateY(-10px) rotate(1.5deg) } }
    @keyframes animeExcited { 0%,100% { transform:translateY(0) rotate(-2deg) scale(1) } 25% { transform:translateY(-7px) rotate(3deg) scale(1.025) } 60% { transform:translateY(-3px) rotate(-1deg) scale(1.01) } }
    @keyframes hairSway { 0%,100% { transform:rotate(-1deg) } 50% { transform:rotate(3deg) } }
    @keyframes animeBlink { 0%,42%,46%,100% { transform:scaleY(1) } 44% { transform:scaleY(.1) } }
    @keyframes starTwinkle { 0%,100% { opacity:.35; transform:scale(.75) rotate(0) } 50% { opacity:1; transform:scale(1.22) rotate(18deg) } }
    @keyframes starDrift { 0%,100% { transform:translate(0,0) rotate(0); opacity:.45 } 50% { transform:translate(-5px,-8px) rotate(22deg); opacity:1 } }
    @keyframes loadingDots { 0% { content:"" } 25% { content:"." } 50% { content:".." } 75%,100% { content:"..." } }
    @media (max-width:640px) { .tm-search-panel { grid-template-columns:minmax(0,1fr) 84px; padding:16px; gap:8px; } .tm-search-character { width:84px; } .tm-search-title { font-size:23px; } .tm-operation-card { gap:10px; padding:10px; } .tm-operation-girl { width:64px; height:64px; flex-basis:64px; } }
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; scroll-behavior: auto !important; }
    }
    </style>
    """.replace("HERO_REPLACE", HERO_IMAGE),
    unsafe_allow_html=True,
)

# Gen-Z motion layer (aurora, scroll reveals, glass nav, shine buttons) added on top of the original CSS.
from ui import theme
theme.inject()


# =========================================================
# NAVIGATION HEADER & INTERACTIVE WORKSPACE TABS
# =========================================================

current_nav = st.session_state.get("tl_workspace_nav", "TravelMate planner")

nav_header_col1, nav_header_col2 = st.columns([1.4, 4.6])
with nav_header_col1:
    st.markdown(
        """
        <div style="display:flex; align-items:center; height:100%; padding-top:6px;">
            <div class="brand" style="margin:0; font-size:26px;">travel<span>mate.</span> <span style="font-size:12px; color:#0f8b78; font-weight:800; background:#e0f2fe; padding:3px 10px; border-radius:12px; margin-left:6px; letter-spacing:0.5px;">TripLedger</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with nav_header_col2:
    t_c1, t_c2, t_c3, t_c4, t_c5, t_c6 = st.columns(6)
    with t_c1:
        if st.button("🌍 Planner", key="top_tab_planner", type="primary" if current_nav == "TravelMate planner" else "secondary", use_container_width=True):
            st.session_state["tl_workspace_nav"] = "TravelMate planner"
            st.rerun()
    with t_c2:
        if st.button("📊 Overview", key="top_tab_overview", type="primary" if current_nav == "Overview" else "secondary", use_container_width=True):
            st.session_state["tl_workspace_nav"] = "Overview"
            st.rerun()
    with t_c3:
        if st.button("🧳 My Trips", key="top_tab_trips", type="primary" if current_nav == "My trips" else "secondary", use_container_width=True):
            st.session_state["tl_workspace_nav"] = "My trips"
            st.rerun()
    with t_c4:
        if st.button("💳 Payments", key="top_tab_payments", type="primary" if current_nav == "Payments" else "secondary", use_container_width=True):
            st.session_state["tl_workspace_nav"] = "Payments"
            st.rerun()
    with t_c5:
        if st.button("📒 Ledger", key="top_tab_ledger", type="primary" if current_nav == "Transaction ledger" else "secondary", use_container_width=True):
            st.session_state["tl_workspace_nav"] = "Transaction ledger"
            st.rerun()
    with t_c6:
        user_tab_label = "👤 " + (st.session_state.get("tl_user", {}).get("email", "").split("@")[0] if st.session_state.get("tl_access_token") else "Account")
        if st.button(user_tab_label, key="top_tab_account", type="primary" if current_nav == "Account & access" else "secondary", use_container_width=True):
            st.session_state["tl_workspace_nav"] = "Account & access"
            st.rerun()

st.markdown("<div style='margin-bottom:14px; border-bottom:1px solid rgba(31,87,72,0.12);'></div>", unsafe_allow_html=True)


# =========================================================
# HELPER: find a place dict by name
# =========================================================

def find_place(name):
    """Return (category_key, place_dict) for the given place name."""
    for cat_key, cat_data in CATEGORIES.items():
        for place in cat_data["places"]:
            if place["name"] == name:
                return cat_key, place
    return None, None


# =========================================================
# DESTINATION SEARCH HELPERS
# =========================================================

def all_destinations():
    """Return the existing catalogue destinations without changing their order."""
    return [place for category in CATEGORIES.values() for place in category["places"]]


def destination_matches(query: str, limit: int = 6):
    """Search the existing destination catalogue; keep matching logic testable."""
    return search_destination_catalog(CATEGORIES, query, limit=limit)


# =========================================================
# PAGE: HOME (Hero landing)
# =========================================================

def render_home():
    st.markdown(
        """
        <section class="hero">
            <div class="hero-content">
                <div class="eyebrow">YOUR NEXT CHAPTER STARTS HERE</div>
                <h1>Somewhere<br>between <em>here</em><br>and extraordinary.</h1>
                <p>
                    Your next unforgettable journey is waiting.
                    Discover beautiful destinations and create
                    a trip that feels uniquely yours.
                </p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(theme.marquee([p["name"] for p in all_destinations()]), unsafe_allow_html=True)

    # Animated destination search, added below the original hero without replacing it.
    st.markdown(
        """
        <div class="tm-search-panel">
          <div>
            <div class="tm-search-kicker">Find your next escape</div>
            <div class="tm-search-title">Where should we take you?</div>
            <p class="tm-search-copy">Search a city, country, island, or hidden getaway.</p>
          </div>
          <svg class="tm-search-character" viewBox="0 0 150 176" role="img" aria-label="Animated anime travel guide with chestnut hair, green eyes, and a mint travel jacket">
            <defs>
              <linearGradient id="tmHair" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#70422f"/><stop offset="1" stop-color="#3e2a27"/></linearGradient>
              <linearGradient id="tmJacket" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#c6e3cf"/><stop offset="1" stop-color="#6f9e86"/></linearGradient>
            </defs>
            <g class="tm-anime-star" fill="#d7aa65"><path d="M20 34l3 7 7 3-7 3-3 7-3-7-7-3 7-3z"/><path d="M126 56l2 5 5 2-5 2-2 5-2-5-5-2 5-2z"/></g>
            <ellipse cx="76" cy="163" rx="42" ry="7" fill="#1f5748" opacity=".10"/>
            <path d="M38 157 Q40 126 54 119 L96 119 Q113 131 115 157Z" fill="url(#tmJacket)"/>
            <path d="M65 121l11 18 11-18-6-7H70Z" fill="#fff8ec"/>
            <g class="tm-anime-hair">
              <path d="M39 65 Q28 23 72 18 Q112 17 116 59 L110 112 Q99 129 91 116 L49 119 Q33 108 39 65Z" fill="url(#tmHair)"/>
              <path d="M43 56 Q45 22 76 25 Q101 23 111 52 Q91 41 80 44 Q59 47 43 56Z" fill="#85523b"/>
            </g>
            <path d="M51 52 Q48 38 58 34 Q75 24 93 38 Q103 46 99 69 L95 94 Q88 111 74 111 Q58 108 52 91Z" fill="#ffd8bd"/>
            <path d="M49 56 Q56 40 72 42 Q88 45 100 56 L99 45 Q90 28 73 30 Q54 30 47 47Z" fill="url(#tmHair)"/>
            <path d="M50 56 Q43 75 51 94 L41 87 Q35 65 43 50Z" fill="#59372c"/>
            <path d="M99 55 Q110 76 98 97 L108 88 Q118 66 105 47Z" fill="#4a3029"/>
            <g class="tm-anime-blink" fill="#477c63"><ellipse cx="62" cy="72" rx="5" ry="7"/><ellipse cx="85" cy="72" rx="5" ry="7"/></g>
            <g fill="#fff"><circle cx="63" cy="70" r="1.8"/><circle cx="86" cy="70" r="1.8"/></g>
            <path d="M69 88 Q75 93 81 88" fill="none" stroke="#c87570" stroke-width="2" stroke-linecap="round"/>
            <circle cx="54" cy="83" r="5" fill="#f4a9a0" opacity=".42"/><circle cx="94" cy="83" r="5" fill="#f4a9a0" opacity=".42"/>
            <path d="M48 42 Q52 24 75 25 Q97 23 106 45 Q91 38 83 39 Q65 39 48 52Z" fill="#70422f"/>
            <path d="M51 46 Q42 64 49 83 Q40 78 39 64 Q39 49 51 46Z" fill="#70422f"/>
            <path d="M94 43 Q107 56 100 79 Q111 72 110 57 Q108 44 94 43Z" fill="#4a3029"/>
            <path d="M60 119l15 20 15-20" fill="none" stroke="#fff8ec" stroke-width="3"/>
            <path d="M105 132l9 10-7 8-9-11Z" fill="#d7aa65"/><path d="M103 139l7 7" stroke="#fff8ec" stroke-width="2"/>
          </svg>
        </div>
        """,
        unsafe_allow_html=True,
    )
    search_col, action_col = st.columns([5, 1.35])
    with search_col:
        search_query = st.text_input(
            "Search destinations",
            key="location_search_input",
            placeholder="Try Kyoto, Goa, Bali, Manali…",
            label_visibility="collapsed",
            help="Search our destination collection or enter any place in the world.",
        )
    with action_col:
        search_clicked = st.button("⌕  Search places", key="location_search_submit", use_container_width=True)

    cleaned_search = (search_query or "").strip()
    if cleaned_search:
        suggestions = destination_matches(cleaned_search, limit=5)
        if suggestions:
            st.caption("✨ Suggested destinations — choose one to open its travel guide")
            suggestion_cols = st.columns(min(3, len(suggestions)))
            for idx, suggested_place in enumerate(suggestions):
                with suggestion_cols[idx % len(suggestion_cols)]:
                    if st.button(
                        f"📍 {suggested_place['name']}",
                        key=f"location_suggestion_{idx}_{suggested_place['name']}",
                        use_container_width=True,
                    ):
                        st.session_state["selected_place"] = suggested_place["name"]
                        st.session_state["custom_destination"] = None
                        st.session_state["page"] = "place_detail"
                        st.rerun()
        if search_clicked:
            matched = suggestions[0] if suggestions else None
            if matched and cleaned_search.casefold() in matched["name"].casefold():
                st.session_state["selected_place"] = matched["name"]
                st.session_state["custom_destination"] = None
                st.session_state["page"] = "place_detail"
                st.rerun()
            else:
                st.session_state["custom_destination"] = cleaned_search
                st.session_state["selected_place"] = None
                st.session_state["page"] = "place_detail"
                st.rerun()
        if not suggestions:
            st.markdown(
                '<div class="tm-search-tip">No exact match in our curated list? Search still works for any location.</div>',
                unsafe_allow_html=True,
            )
        st.link_button("🌐 View destination on Google Maps", google_location_search_url(cleaned_search), use_container_width=True)
    else:
        st.markdown('<div class="tm-search-tip">Tip: type a few letters, choose a suggestion, or search any location directly.</div>', unsafe_allow_html=True)

    # CTA button ─ "Your journey, thoughtfully planned"
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if st.button("✦  Your journey, thoughtfully planned", key="hero_cta", use_container_width=False):
        st.session_state["page"] = "explore"
        st.rerun()

    # Features strip
    st.markdown(
        """
        <div class="section">
            <div class="section-kicker">TRAVEL, YOUR WAY</div>
            <div class="section-title">Less planning stress. More wonder.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    feature_columns = st.columns(4)

    features = [
        ("🧭", "Thoughtful routes", "Start with your origin and destination."),
        ("💰", "Budget conscious", "Plan around your travel budget."),
        ("🌿", "Your interests", "Choose the experiences you love."),
        ("✈️", "Ready to explore", "Turn your travel ideas into a plan."),
    ]

    for column, feature in zip(feature_columns, features):
        with column:
            st.markdown(
                f"""
                <div class="feature">
                    <div class="feature-icon">{feature[0]}</div>
                    <div class="feature-title">{feature[1]}</div>
                    <div class="feature-desc">{feature[2]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        theme.stats([
            (len(all_destinations()), "Destinations"),
            (len(CATEGORIES), "Travel moods"),
            (4, "AI agents"),
            (4, "Export formats"),
        ]) + theme.bento(),
        unsafe_allow_html=True,
    )


# =========================================================
# PAGE: EXPLORE (Categories + Places)
# =========================================================

def render_explore():
    # Back button
    if st.button("← Back to Home", key="back_to_home"):
        st.session_state["page"] = "home"
        st.session_state["selected_category"] = None
        st.rerun()

    st.markdown(
        """
        <div class="section" style="padding-top:10px;">
            <div class="section-kicker">A LITTLE INSPIRATION</div>
            <div class="section-title">Places that stay with you.</div>
            <div class="section-desc">
                From quiet coastlines to mountain escapes,
                find the feeling you want to travel for.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ─── Category selector tabs ───
    cat_keys = list(CATEGORIES.keys())
    cat_columns = st.columns(len(cat_keys) + 1)

    with cat_columns[0]:
        st.markdown(
            """
            <div class="category-tab">
                <div class="cat-icon">🌍</div>
                <div class="cat-title">ALL DESTINATIONS</div>
                <div class="cat-desc">Browse all options across every category</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Show All Places", key="cat_all", use_container_width=True):
            st.session_state["selected_category"] = None
            st.rerun()

    for col, cat_key in zip(cat_columns[1:], cat_keys):
        cat = CATEGORIES[cat_key]
        with col:
            st.markdown(
                f"""
                <div class="category-tab">
                    <div class="cat-icon">{cat["icon"]}</div>
                    <div class="cat-title">{cat_key}</div>
                    <div class="cat-desc">{len(cat["places"])} places · {cat["description"]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                f"Browse {cat_key.title()}",
                key=f"cat_{cat_key}",
                use_container_width=True,
            ):
                st.session_state["selected_category"] = cat_key
                st.rerun()

    # ─── Show places for selected category or all categories ───
    selected_cat = st.session_state.get("selected_category")

    if selected_cat and selected_cat in CATEGORIES:
        cats_to_display = [selected_cat]
        if st.button("← Show All Categories", key="show_all_btn"):
            st.session_state["selected_category"] = None
            st.rerun()
    else:
        cats_to_display = cat_keys

    for cat_name in cats_to_display:
        cat_data = CATEGORIES[cat_name]
        st.markdown(
            f"""
            <div class="section" style="padding-top: 35px; padding-bottom: 12px;">
                <div class="section-kicker">{cat_name}</div>
                <div class="section-title">{cat_data["icon"]}  {cat_name.title()} Destinations <span style="font-size:20px; font-weight:normal; color:var(--muted);">({len(cat_data["places"])} places)</span></div>
                <div class="section-desc">{cat_data["description"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        places = cat_data["places"]
        row_size = 3
        for row_start in range(0, len(places), row_size):
            row_items = places[row_start : row_start + row_size]
            cols = st.columns(3)
            for col_idx, place in enumerate(row_items):
                with cols[col_idx]:
                    st.markdown(
                        f"""
                        <div class="destination-card"
                            style="background-image: url('{place["image"]}');">
                            <div class="destination-overlay">
                                <div class="destination-tag">{cat_name}</div>
                                <div class="destination-name">{html.escape(place["name"])}</div>
                                <div class="destination-desc">{place["description"][:60]}…</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if st.button(
                        f"Explore {place['name']}  →",
                        key=f"place_{cat_name}_{place['name']}_{row_start + col_idx}",
                        use_container_width=True,
                    ):
                        st.session_state["selected_place"] = place["name"]
                        st.session_state["page"] = "place_detail"
                        st.rerun()


# =========================================================
# PAGE: PLACE DETAIL + TRAVEL PLANNER
# =========================================================

def render_place_detail():
    place_name = st.session_state.get("selected_place")
    cat_key, place = find_place(place_name)
    custom_destination = (st.session_state.get("custom_destination") or "").strip()
    is_custom_destination = not place and bool(custom_destination)

    if is_custom_destination:
        # User-entered locations work even when they are not in the curated destination catalogue.
        place = {
            "name": custom_destination,
            "description": "A trip tailored around your chosen destination. Use the planner below to create your itinerary.",
            "image": HERO_IMAGE,
            "highlights": ["Explore local highlights", "Discover food and culture", "Build a day-by-day plan"],
            "best_time": "Check local seasonal conditions",
            "avg_budget": "Set your own budget",
        }
        cat_key = "SEARCHED DESTINATION"
    elif not place:
        st.error("Place not found. Search again or choose a curated destination.")
        st.session_state["page"] = "home"
        st.rerun()
        return

    # Back button
    if st.button("← Back to Home" if is_custom_destination else "← Back to Explore", key="back_to_explore"):
        st.session_state["page"] = "home" if is_custom_destination else "explore"
        if not is_custom_destination:
            st.session_state["selected_category"] = cat_key
        st.rerun()

    # Breadcrumb
    st.markdown(
        f"""
        <div class="breadcrumb">
            <span>Home</span>
            <span class="sep">›</span>
            <span>{cat_key.title()}</span>
            <span class="sep">›</span>
            <span class="current">{html.escape(place["name"])}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Place hero banner
    st.markdown(
        f"""
        <div class="place-hero" style="background-image: url('{html.escape(place["image"], quote=True)}');">
            <div class="place-hero-overlay"></div>
            <div class="place-hero-content">
                <div class="destination-tag" style="margin-bottom:12px;">{html.escape(cat_key)}</div>
                <h1>{html.escape(place["name"])}</h1>
                <p>{html.escape(place["description"])}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # Info cards row
    info_cols = st.columns(3)
    with info_cols[0]:
        st.markdown(
            f"""
            <div class="info-card">
                <div class="info-label">🗓️ Best Time to Visit</div>
                <div class="info-value">{place["best_time"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with info_cols[1]:
        st.markdown(
            f"""
            <div class="info-card">
                <div class="info-label">💰 Avg. Budget</div>
                <div class="info-value">{place["avg_budget"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with info_cols[2]:
        st.markdown(
            f"""
            <div class="info-card">
                <div class="info-label">📍 Category</div>
                <div class="info-value">{cat_key.title()}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Highlights
    st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="section-kicker">HIGHLIGHTS</div>
        """,
        unsafe_allow_html=True,
    )
    chips_html = "".join(
        f'<span class="highlight-chip">{html.escape(str(h))}</span>' for h in place["highlights"]
    )
    st.markdown(f"<div>{chips_html}</div>", unsafe_allow_html=True)
    if is_custom_destination:
        st.link_button(
            "📍 View destination on Google Maps",
            google_location_search_url(custom_destination),
            use_container_width=True,
        )

    # ─── Travel Plan Form ───

    st.markdown(
        f"""
        <div class="section">
            <div class="section-kicker">YOUR ADVENTURE BEGINS</div>
            <div class="section-title">Plan your trip to {html.escape(place["name"])}</div>
            <div class="section-desc">
                Tell us a little about your trip.
                Your travel planner will take it from here.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown("### ✈️ Create your travel plan")
        st.markdown(
            '<div class="form-caption">'
            'Add your details below to get started.'
            '</div>',
            unsafe_allow_html=True,
        )

        with st.form("travel_planner_form"):
            col1, col2 = st.columns(2)

            with col1:
                origin = st.text_input(
                    "📍 Starting location",
                    placeholder="e.g. Pune",
                )

            with col2:
                # Pre-fill destination from selected place
                destination = st.text_input(
                    "🌍 Where do you want to go?",
                    value=place["name"].split(",")[0],
                    placeholder="e.g. Goa",
                )

            col3, col4 = st.columns(2)

            with col3:
                start_date = st.date_input(
                    "🗓️ Departure date",
                    value=date.today() + timedelta(days=7),
                    min_value=date.today(),
                )

            with col4:
                end_date = st.date_input(
                    "🗓️ Return date",
                    value=date.today() + timedelta(days=12),
                    min_value=date.today(),
                )

            col5, col6 = st.columns(2)

            with col5:
                budget = st.number_input(
                    "💰 Total budget (₹)",
                    min_value=1,
                    value=15000,
                    step=1000,
                )

            with col6:
                travelers = st.number_input(
                    "👥 Number of travelers",
                    min_value=1,
                    max_value=50,
                    value=2,
                    step=1,
                )

            # Pre-select preferences based on place highlights
            all_preferences = [
                "Adventure",
                "Nature",
                "Beaches",
                "Historical Places",
                "Food",
                "Shopping",
                "Relaxation",
                "Culture",
            ]
            # Auto-suggest relevant preferences from highlights
            suggested = []
            highlight_lower = [h.lower() for h in place["highlights"]]
            for pref in all_preferences:
                if any(pref.lower() in hl or hl in pref.lower() for hl in highlight_lower):
                    suggested.append(pref)
            if not suggested:
                suggested = ["Nature"]

            preferences = st.multiselect(
                "✨ What would you love to experience?",
                all_preferences,
                default=suggested,
            )

            # Additional planning controls; existing visual structure is retained.
            extra_col1, extra_col2 = st.columns(2)
            with extra_col1:
                travel_pace = st.selectbox(
                    "🧭 Preferred travel pace",
                    ["Relaxed", "Balanced", "Packed"],
                    index=1,
                    help="Used to guide the itinerary density when supported by the planner.",
                )
            with extra_col2:
                accommodation = st.selectbox(
                    "🛏️ Accommodation style",
                    ["Any", "Budget", "Comfort", "Luxury"],
                    help="A preference for recommendations; prices remain estimates.",
                )

            submitted = st.form_submit_button(
                "Plan My Trip  →",
                use_container_width=True,
            )

    # ─── Execute planner ───

    if submitted:
        validation_errors = validate_trip(origin, destination, start_date, end_date, budget, travelers)
        if validation_errors:
            for validation_error in validation_errors:
                st.error(validation_error)
        else:
            st.markdown(
                """
                <div class="section">
                    <div class="section-kicker">MADE FOR YOU</div>
                    <div class="section-title">Your journey is taking shape.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            operation_slot = st.empty()  # holds the "planning" card so it can be removed once the plan is ready
            try:
                operation_slot.markdown(
                    """
                    <div class="tm-operation-card" role="status" aria-live="polite">
                      <svg class="tm-operation-girl" viewBox="0 0 150 176" role="img" aria-label="Travel guide thinking and planning your journey">
                        <defs><linearGradient id="opHair" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#87533b"/><stop offset="1" stop-color="#3e2a27"/></linearGradient><linearGradient id="opCoat" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#c6e3cf"/><stop offset="1" stop-color="#6f9e86"/></linearGradient></defs>
                        <circle cx="76" cy="83" r="62" fill="#dceee2" opacity=".72"/>
                        <g fill="#d7aa65" class="tm-anime-star"><path d="M20 34l3 7 7 3-7 3-3 7-3-7-7-3 7-3z"/><path d="M126 56l2 5 5 2-5 2-2 5-2-5-5-2 5-2z"/></g>
                        <path d="M38 157Q40 126 54 119L96 119Q113 131 115 157Z" fill="url(#opCoat)"/><path d="M65 121l11 18 11-18-6-7H70Z" fill="#fff8ec"/>
                        <g class="tm-anime-hair"><path d="M39 65Q28 23 72 18Q112 17 116 59L110 112Q99 129 91 116L49 119Q33 108 39 65Z" fill="url(#opHair)"/><path d="M43 56Q45 22 76 25Q101 23 111 52Q91 41 80 44Q59 47 43 56Z" fill="#85523b"/></g>
                        <path d="M51 52Q48 38 58 34Q75 24 93 38Q103 46 99 69L95 94Q88 111 74 111Q58 108 52 91Z" fill="#ffd8bd"/><path d="M49 56Q56 40 72 42Q88 45 100 56L99 45Q90 28 73 30Q54 30 47 47Z" fill="url(#opHair)"/>
                        <path d="M50 56Q43 75 51 94L41 87Q35 65 43 50Z" fill="#59372c"/><path d="M99 55Q110 76 98 97L108 88Q118 66 105 47Z" fill="#4a3029"/>
                        <g class="tm-anime-blink" fill="#477c63"><ellipse cx="62" cy="72" rx="5" ry="7"/><ellipse cx="85" cy="72" rx="5" ry="7"/></g><g fill="#fff"><circle cx="63" cy="70" r="1.8"/><circle cx="86" cy="70" r="1.8"/></g>
                        <path d="M68 87Q75 96 83 87" fill="none" stroke="#c87570" stroke-width="2.5" stroke-linecap="round"/><circle cx="54" cy="83" r="5" fill="#f4a9a0" opacity=".5"/><circle cx="94" cy="83" r="5" fill="#f4a9a0" opacity=".5"/>
                        <path d="M48 42Q52 24 75 25Q97 23 106 45Q91 38 83 39Q65 39 48 52Z" fill="#70422f"/><path d="M51 46Q42 64 49 83Q40 78 39 64Q39 49 51 46Z" fill="#70422f"/><path d="M94 43Q107 56 100 79Q111 72 110 57Q108 44 94 43Z" fill="#4a3029"/>
                        <g stroke="#d7aa65" stroke-width="2" fill="none" stroke-linecap="round"><path d="M111 36q8 -8 14 0"/><path d="M119 28v16"/></g>
                      </svg>
                      <div><div class="tm-operation-title">Your travel buddy is on it<span class="tm-operation-dots"></span></div><p class="tm-operation-copy">Comparing ideas, organising your itinerary, and bringing your trip together.</p></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                with st.spinner(
                    "🌍 Your travel planner is preparing your trip..."
                ):
                    request = TripRequest(
                        destination=destination.strip(),
                        origin=origin.strip(),
                        start_date=start_date.isoformat(),
                        end_date=end_date.isoformat(),
                        budget=float(budget),
                        travelers=travelers,
                        preferences=preferences,
                        pace=travel_pace,
                        accommodation=accommodation,
                    )
                    request_key = trip_fingerprint(
                        origin, destination, start_date, end_date, budget, travelers,
                        preferences, travel_pace, accommodation,
                    )
                    cached_plan = st.session_state.get("travelmate_plan_cache", {})
                    def generate_plan():
                        return CoordinatorAgent().run(request)
                    plan, was_reused = get_or_create_cached_plan(cached_plan, request_key, generate_plan, max_entries=3)
                    st.session_state["travelmate_plan_cache"] = cached_plan
                    if was_reused:
                        st.info("Reused your recently generated plan for the same trip, preventing duplicate processing.")
                    st.session_state["travelmate_last_plan"] = plan
                operation_slot.empty()

                # ─── Trip header ───
                num_days = (end_date - start_date).days
                best_flight = min(plan.flights, key=lambda f: f.price) if plan.flights else None
                best_hotel = min(plan.hotels, key=lambda h: h.price_per_night) if plan.hotels else None

                st.markdown(
                    f"""
                    <div class="trip-header">
                        <div class="trip-route">{html.escape(origin.strip())}  ✈  {html.escape(destination.strip())}</div>
                        <div class="trip-dates">🗓️ {start_date.strftime('%b %d, %Y')} — {end_date.strftime('%b %d, %Y')}</div>
                        <div class="trip-stats">
                            <div class="trip-stat">
                                <div class="stat-value">{num_days}</div>
                                <div class="stat-label">Days</div>
                            </div>
                            <div class="trip-stat">
                                <div class="stat-value">{travelers}</div>
                                <div class="stat-label">Travelers</div>
                            </div>
                            <div class="trip-stat">
                                <div class="stat-value">₹{budget:,.0f}</div>
                                <div class="stat-label">Budget</div>
                            </div>
                            <div class="trip-stat">
                                <div class="stat-value">{len(plan.itinerary)}</div>
                                <div class="stat-label">Days Planned</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # ─── Flights section ───
                if plan.flights:
                    st.markdown(
                        """
                        <div class="plan-section-header">
                            <span class="ps-icon">✈️</span>
                            <span class="ps-title">Flight Options</span>
                            <span class="ps-line"></span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    sorted_flights = sorted(plan.flights, key=lambda f: f.price)
                    for i, f in enumerate(sorted_flights):
                        badge = '<span class="fc-badge">Best Price</span>' if i == 0 else ''
                        st.markdown(
                            f"""
                            <div class="flight-card">
                                <div>
                                    <div class="fc-airline">{html.escape(str(f.airline))} {badge}</div>
                                    <div class="fc-route">{html.escape(str(f.departure))} → {html.escape(str(f.arrival))}</div>
                                </div>
                                <div class="fc-duration">{f.duration_hours}h</div>
                                <div class="fc-price">₹{f.price:,.0f}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                # ─── Hotels section ───
                if plan.hotels:
                    st.markdown(
                        """
                        <div class="plan-section-header">
                            <span class="ps-icon">🏨</span>
                            <span class="ps-title">Recommended Hotels</span>
                            <span class="ps-line"></span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    hotel_cols = st.columns(min(len(plan.hotels), 3))
                    for col, h in zip(hotel_cols, plan.hotels):
                        stars = '★' * max(0, min(5, int(round(h.rating)))) + '☆' * (5 - max(0, min(5, int(round(h.rating)))))
                        safe_hotel_display = html.escape(str(h.name))
                        safe_neighborhood_display = html.escape(str(h.neighborhood))
                        with col:
                            st.markdown(
                                f"""
                                <div class="hotel-card">
                                    <div class="hc-top">
                                        <div class="hc-name">{safe_hotel_display}</div>
                                        <div class="hc-rating">★ {float(h.rating):.1f}</div>
                                    </div>
                                    <div class="hc-neighborhood">📍 {safe_neighborhood_display} · {stars}</div>
                                    <div class="hc-price">₹{h.price_per_night:,.0f} <span>/ night</span></div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                            # Click-through hotel discovery: real Google search results, maps, photos and reviews.
                            safe_hotel_name = str(h.name).strip()
                            maps_url = google_maps_search_url(safe_hotel_name, destination)
                            photos_url = google_hotel_photos_url(safe_hotel_name, destination)
                            link_col1, link_col2 = st.columns(2)
                            with link_col1:
                                st.link_button("📍 View location", maps_url, use_container_width=True)
                            with link_col2:
                                st.link_button("📸 Photos & reviews", photos_url, use_container_width=True)
                            st.markdown('<div class="hotel-link-caption">Opens Google results in a new browser tab. Verify current prices, ratings and availability with the provider.</div>', unsafe_allow_html=True)

                # ─── Weather section ───
                if plan.weather:
                    st.markdown(
                        """
                        <div class="plan-section-header">
                            <span class="ps-icon">🌤️</span>
                            <span class="ps-title">Weather Forecast</span>
                            <span class="ps-line"></span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    def weather_emoji(summary: str) -> str:
                        s = summary.lower()
                        if 'clear' in s or 'sunny' in s:
                            return '☀️'
                        elif 'mainly clear' in s:
                            return '🌤️'
                        elif 'partly' in s:
                            return '⛅'
                        elif 'overcast' in s:
                            return '☁️'
                        elif 'fog' in s:
                            return '🌫️'
                        elif 'drizzle' in s:
                            return '🌦️'
                        elif 'snow' in s or 'freezing' in s:
                            return '❄️'
                        elif 'thunder' in s or 'storm' in s:
                            return '⛈️'
                        elif 'rain' in s or 'shower' in s:
                            return '🌧️'
                        elif 'cloud' in s:
                            return '☁️'
                        return '🌤️'

                    # Show weather cards — up to 7 days, in rows of 3-4
                    display_weather = plan.weather[:7]
                    # Split into rows for clean layout
                    row_size = min(len(display_weather), 4)
                    for row_start in range(0, len(display_weather), row_size):
                        row_items = display_weather[row_start:row_start + row_size]
                        weather_cols = st.columns(len(row_items))
                        for col, w in zip(weather_cols, row_items):
                            icon = weather_emoji(w.summary)
                            with col:
                                st.html(
                                    f'<div class="weather-card">'
                                    f'<div class="wc-day">{html.escape(str(w.date))}</div>'
                                    f'<div class="wc-icon">{icon}</div>'
                                    f'<div class="wc-summary">{html.escape(str(w.summary))}</div>'
                                    f'<div class="wc-temps"><strong>{w.high_c}&deg;</strong> / {w.low_c}&deg;C</div>'
                                    f'</div>'
                                )

                # ─── Itinerary section ───
                if plan.itinerary:
                    st.markdown(
                        """
                        <div class="plan-section-header">
                            <span class="ps-icon">📋</span>
                            <span class="ps-title">Day-by-Day Itinerary</span>
                            <span class="ps-line"></span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    for day in plan.itinerary:
                        acts = ''.join(
                            f'<div class="id-activity"><span class="act-dot"></span>{html.escape(str(act))}</div>'
                            for act in day.activities
                        )
                        st.html(
                            f'<div class="itinerary-day">'
                            f'<div class="id-label">Day {day.day_number}</div>'
                            f'<div class="id-date">{html.escape(str(day.date))}</div>'
                            f'{acts}'
                            f'</div>'
                        )

                # ─── Budget intelligence and portable exports ───
                st.markdown(
                    """
                    <div class="plan-section-header">
                        <span class="ps-icon">💰</span>
                        <span class="ps-title">Budget Snapshot</span>
                        <span class="ps-line"></span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                breakdown = budget_breakdown(plan, num_days)
                budget_cols = st.columns(3)
                for idx, (label, amount) in enumerate(list(breakdown.items())[:6]):
                    with budget_cols[idx % 3]:
                        st.metric(label, f"₹{amount:,.0f}")
                estimated_core = breakdown["Flights (estimate)"] + breakdown["Accommodation (estimate)"]
                if estimated_core > float(budget):
                    st.warning("Your estimated flight and accommodation costs already exceed the entered budget. Review the options before making reservations.")
                else:
                    st.caption("Food, local transport, activities and contingency are suggested allocations, not provider quotes.")

                # ─── 🚀 Seamless TripLedger AI Bridge (1-Click Save & PayPal Checkout) ───
                st.markdown(
                    """
                    <div style="background: linear-gradient(135deg, #0e483f 0%, #173d34 100%); border-radius: 18px; padding: 22px; margin: 24px 0 16px; border: 1px solid #1f5d50; box-shadow: 0 10px 25px rgba(15,139,120,0.18); color: white;">
                        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                            <div>
                                <span style="background: #2dd4bf; color: #0f3d34; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 999px; letter-spacing: 1px; text-transform: uppercase;">PayPal Hackathon Ready</span>
                                <h3 style="margin: 8px 0 4px; color: #ffffff; font-size: 22px; font-weight: 800;">🔒 Lock & Fund This Trip with TripLedger</h3>
                                <p style="margin: 0; color: #a7f3d0; font-size: 14px;">Instant bridge: Store trip to your secure ledger and proceed straight to PayPal Sandbox checkout.</p>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                
                bridge_cols = st.columns([2, 1])
                with bridge_cols[0]:
                    sel_curr = st.selectbox("Fund in Currency", ["USD", "EUR", "GBP", "SGD", "AUD", "CAD", "JPY"], index=0, key="bridge_currency")
                with bridge_cols[1]:
                    # Approximate conversion from INR estimate to selected currency for immediate demo
                    approx_rates = {"USD": 85.0, "EUR": 92.0, "GBP": 108.0, "SGD": 64.0, "AUD": 55.0, "CAD": 62.0, "JPY": 0.55}
                    converted_val = round(float(budget) / approx_rates.get(sel_curr, 85.0), 2 if sel_curr != "JPY" else 0)
                    approved_budget = st.number_input(f"Approved Budget ({sel_curr})", min_value=1.0, value=max(10.0, converted_val), step=10.0, key="bridge_budget")

                if st.button("✨ Save Trip & Proceed to PayPal Checkout ➔", type="primary", use_container_width=True, key="btn_bridge_save"):
                    if not st.session_state.get("tl_access_token"):
                        st.session_state["tl_pending_bridge_trip"] = {
                            "origin": origin.strip(),
                            "destination": destination.strip(),
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat(),
                            "travelers": int(travelers),
                            "budget_amount": f"{approved_budget:.{exponent(sel_curr)}f}",
                            "budget_currency": sel_curr
                        }
                        st.warning("⚠️ Sign in is required to register this trip into your encrypted ledger. Click below to continue:")
                        c_b1, c_b2 = st.columns(2)
                        with c_b1:
                            if st.button("👉 Go to Account & Sign In", key="bridge_goto_acc", type="primary", use_container_width=True):
                                st.session_state["tl_workspace_nav"] = "Account & access"
                                st.rerun()
                        with c_b2:
                            if st.button("⚡ 1-Click Judge Demo Sign-In", key="bridge_demo_sign", type="secondary", use_container_width=True):
                                from ui.tripledger_portal import api
                                demo_mail = "judge@paypalhackathon.com"
                                demo_pw = "Hackathon2026!Demo"
                                try:
                                    res = api("POST", "/api/auth/register", data={"email": demo_mail, "password": demo_pw}, authenticated=False)
                                    st.session_state["tl_access_token"] = res["access_token"]
                                    st.session_state["tl_user"] = res["user"]
                                    st.rerun()
                                except Exception:
                                    try:
                                        res = api("POST", "/api/auth/login", data={"email": demo_mail, "password": demo_pw}, authenticated=False)
                                        st.session_state["tl_access_token"] = res["access_token"]
                                        st.session_state["tl_user"] = res["user"]
                                        st.rerun()
                                    except Exception as err:
                                        st.error(f"Sign-in error: {err}")
                    else:
                        try:
                            from ui.tripledger_portal import api, exponent
                            amount_fmt = f"{approved_budget:.{exponent(sel_curr)}f}"
                            res = api("POST", "/api/trips", data={
                                "origin": origin.strip(),
                                "destination": destination.strip(),
                                "start_date": start_date.isoformat(),
                                "end_date": end_date.isoformat(),
                                "travelers": int(travelers),
                                "budget_amount": amount_fmt,
                                "budget_currency": sel_curr
                            })
                            st.session_state["tl_last_saved_trip"] = res
                            st.session_state["tl_workspace_nav"] = "Payments"
                            st.success(f"Trip #{res['id']} registered in TripLedger! Redirecting to Payments...")
                            st.rerun()
                        except Exception as b_err:
                            st.error(f"Failed to bridge trip: {b_err}")

                st.markdown("#### 📥 Save or share your trip")
                export_cols = st.columns(3)
                trip_json = json.dumps(trip_to_dict(plan), ensure_ascii=False, indent=2, default=str)
                trip_text = trip_to_text(plan)
                with export_cols[0]:
                    st.download_button("Download JSON", data=trip_json, file_name="travelmate-trip.json", mime="application/json", use_container_width=True)
                with export_cols[1]:
                    st.download_button("Download TXT", data=trip_text, file_name="travelmate-itinerary.txt", mime="text/plain", use_container_width=True)
                with export_cols[2]:
                    try:
                        st.download_button("Download PDF", data=trip_to_pdf(plan), file_name="travelmate-itinerary.pdf", mime="application/pdf", use_container_width=True)
                    except ImportError:
                        st.caption("Install reportlab to enable PDF export.")
                try:
                    st.download_button("Download DOCX", data=trip_to_docx(plan), file_name="travelmate-itinerary.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
                except ImportError:
                    st.caption("Install python-docx to enable Word export.")

                # ─── Trip footer ───
                st.markdown(
                    """
                    <div class="trip-footer">
                        <div class="tf-text">Your adventure awaits ✨</div>
                        <div class="tf-sub">This plan was generated by TravelMate's multi-agent system. Prices and availability may vary.</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            except Exception as error:
                operation_slot.empty()
                st.error(f"Unable to generate your travel plan: {error}")
                with st.expander("Technical details"):
                    import traceback
                    st.code(traceback.format_exc())


# =========================================================
# WORKSPACE ROUTER
# =========================================================

portal_choice = st.session_state.get("tl_workspace_nav", "TravelMate planner")

if portal_choice == "TravelMate planner":
    page = st.session_state.get("page", "home")
    if page == "home":
        render_home()
    elif page == "explore":
        render_explore()
    elif page == "place_detail":
        render_place_detail()
    else:
        render_home()
elif portal_choice == "Overview":
    tripledger_portal.render_dashboard()
elif portal_choice == "My trips":
    tripledger_portal.render_trips()
elif portal_choice == "Payments":
    tripledger_portal.render_payments()
elif portal_choice == "Transaction ledger":
    tripledger_portal.render_ledger()
else:
    tripledger_portal.render_account()


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div class="footer">
        <div style="font-size:18px;font-weight:700;color:#214a3d;">
            travelmate.
        </div>
        Made for the journeys that become your favourite stories.<br>
        Travel thoughtfully. Explore endlessly.
    </div>
    """,
    unsafe_allow_html=True,
)