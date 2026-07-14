"""Generate sample Yelp-format data for testing the pipeline."""
import json
import os
import random

# Paths
RAW_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base", "raw_data")
os.makedirs(RAW_DATA_DIR, exist_ok=True)

# Sample data
CITIES = [("Philadelphia", "PA"), ("Tampa", "FL"), ("Indianapolis", "IN"), ("Nashville", "TN"), ("Phoenix", "AZ")]
CATEGORIES_LIST = [
    ["Restaurants", "Italian"], ["Restaurants", "Chinese"], ["Restaurants", "Mexican"],
    ["Restaurants", "Japanese"], ["Restaurants", "American (Traditional)"],
    ["Coffee & Tea"], ["Bakeries"], ["Bars", "Nightlife"], ["Fast Food", "Burgers"],
    ["Shopping", "Fashion"], ["Automotive", "Auto Repair"], ["Home Services", "Plumbing"],
]
BUSINESS_NAMES = [
    "Joe's Pizza", "Golden Dragon", "El Patron", "Sakura Sushi", "Burger King",
    "Starbucks", "Sweet Treats Bakery", "The Irish Pub", "McDonald's", "Fashion Outlet",
    "Auto Pro Shop", "Quick Fix Plumbing", "Mama Mia Italian", "Pho 99", "Taco Fiesta",
    "Dunkin Donuts", "Whole Foods", "The Gym Spot", "Nail Spa", "Pet Paradise",
    "Best Cuts Barbershop", "Green Garden Vegan", "BBQ Heaven", "Sushi Train",
    "Pizza Hut", "Thai Spice", "Wine & Dine", "Car Wash Express", "Dry Clean Pro",
    "Book Worm Cafe", "24 Hour Fitness", "Comfort Inn", "Tech Repair Shop",
    "Sunrise Diner", "Lucky Strike Bowling", "Artisan Coffee House", "Mediterranean Grill",
    "Ice Cream Dream", "Budget Motel", "City Dental", "Happy Nails", "Toy Kingdom",
    "Fresh Mart Grocery", "Speedy Oil Change", "Downtown Apartments", "Jazz & Blues Club",
    "The Steakhouse", "Smoothie King", "Hair & Beauty Salon", "Pet Vet Clinic",
]

REVIEW_TEXTS = [
    "Great food and excellent service! The atmosphere was wonderful and I would definitely come back.",
    "Decent place but a bit overpriced. The staff was friendly though.",
    "Absolutely loved it here! Best {category} in town. Highly recommend the special.",
    "Not impressed. The wait was too long and the food was just average.",
    "A hidden gem! The food was amazing and the prices were very reasonable.",
    "Good place for a quick bite. Nothing fancy but gets the job done.",
    "The ambiance is fantastic and the staff goes above and beyond.",
    "Disappointing experience. The food was cold and the service was slow.",
    "One of my favorite spots! Always consistent quality and great value.",
    "Pretty good overall. Would give it 4 stars. The dessert was the highlight.",
    "Excellent! The flavors were authentic and the portions were generous.",
    "Terrible service today. Usually it's better but this visit was a letdown.",
    "Cozy atmosphere with delicious food. Perfect for a date night.",
    "Solid {stars}-star experience. Met expectations but didn't exceed them.",
    "Wow! Blown away by the quality. Will definitely be returning soon.",
    "Average at best. There are better options in the area for the price.",
    "Really enjoyed our meal here. Everything was fresh and flavorful.",
    "Not worth the hype. The reviews made it seem much better than it actually is.",
    "Wonderful family-friendly place with great options for kids.",
    "The best meal I've had in months! Every dish was perfectly prepared.",
]


def generate_businesses(n=5000):
    """Generate sample business data in Yelp format."""
    filepath = os.path.join(RAW_DATA_DIR, "yelp_academic_dataset_business.json")
    print(f"Generating {n} businesses -> {filepath}")
    with open(filepath, "w", encoding="utf-8") as f:
        for i in range(n):
            city, state = random.choice(CITIES)
            stars = round(random.uniform(1.0, 5.0), 1)
            categories = random.choice(CATEGORIES_LIST)
            is_open = random.choice([False, True])
            review_count = random.randint(3, 1000)
            business = {
                "business_id": f"b{i:06d}",
                "name": random.choice(BUSINESS_NAMES) + (f" #{random.randint(1,99)}" if random.random() < 0.3 else ""),
                "address": f"{random.randint(100, 9999)} {random.choice(['Main St', 'Broadway', 'Oak Ave', 'Elm St', 'Market St', 'Park Blvd'])}",
                "city": city,
                "state": state,
                "postal_code": f"{random.randint(10000, 99999)}",
                "latitude": round(random.uniform(25.0, 48.0), 6),
                "longitude": round(random.uniform(-125.0, -70.0), 6),
                "stars": stars,
                "review_count": review_count,
                "is_open": is_open,
                "attributes": {
                    "RestaurantsTakeOut": random.choice([True, False]),
                    "BusinessParking": {
                        "garage": random.choice([True, False]),
                        "street": random.choice([True, False]),
                        "validated": random.choice([True, False]),
                        "lot": random.choice([True, False]),
                        "valet": random.choice([True, False]),
                    },
                },
                "categories": ", ".join(categories),
                "hours": {
                    "Monday": f"{random.randint(6,11)}:00-{random.randint(20,23)}:00",
                    "Tuesday": f"{random.randint(6,11)}:00-{random.randint(20,23)}:00",
                    "Wednesday": f"{random.randint(6,11)}:00-{random.randint(20,23)}:00",
                    "Thursday": f"{random.randint(6,11)}:00-{random.randint(20,23)}:00",
                    "Friday": f"{random.randint(6,11)}:00-{random.randint(22,23)}:00",
                    "Saturday": f"{random.randint(7,12)}:00-{random.randint(22,23)}:00",
                    "Sunday": f"{random.randint(8,12)}:00-{random.randint(18,22)}:00",
                },
            }
            f.write(json.dumps(business) + "\n")
    print(f"  Done: {n} records")


def generate_reviews(n=20000):
    """Generate sample review data in Yelp format."""
    filepath = os.path.join(RAW_DATA_DIR, "yelp_academic_dataset_review.json")
    print(f"Generating {n} reviews -> {filepath}")
    with open(filepath, "w", encoding="utf-8") as f:
        for i in range(n):
            business_id = f"b{random.randint(0, 4999):06d}"
            stars = random.randint(1, 5)
            review = {
                "review_id": f"r{i:08d}",
                "user_id": f"u{random.randint(0, 19999):06d}",
                "business_id": business_id,
                "stars": stars,
                "useful": random.randint(0, 50),
                "funny": random.randint(0, 20),
                "cool": random.randint(0, 30),
                "text": random.choice(REVIEW_TEXTS).format(
                    category=random.choice(["Italian", "Chinese", "Mexican", "food", "coffee"]),
                    stars=stars,
                ),
                "date": f"202{random.randint(0,3)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            }
            f.write(json.dumps(review) + "\n")
    print(f"  Done: {n} records")


def generate_checkins(n=20000):
    """Generate sample check-in data."""
    filepath = os.path.join(RAW_DATA_DIR, "yelp_academic_dataset_checkin.json")
    print(f"Generating {n} check-ins -> {filepath}")
    with open(filepath, "w", encoding="utf-8") as f:
        for i in range(n):
            checkin = {
                "business_id": f"b{random.randint(0, 4999):06d}",
                "date": ",".join(
                    f"202{random.randint(0,3)}-{random.randint(1,12):02d}-{random.randint(1,28):02d} {random.randint(0,23):02d}:{random.randint(0,59):02d}"
                    for _ in range(random.randint(1, 20))
                ),
            }
            f.write(json.dumps(checkin) + "\n")
    print(f"  Done: {n} records")


def generate_tips(n=20000):
    """Generate sample tip data."""
    filepath = os.path.join(RAW_DATA_DIR, "yelp_academic_dataset_tip.json")
    print(f"Generating {n} tips -> {filepath}")
    with open(filepath, "w", encoding="utf-8") as f:
        for i in range(n):
            tip = {
                "user_id": f"u{random.randint(0, 19999):06d}",
                "business_id": f"b{random.randint(0, 4999):06d}",
                "text": random.choice([
                    "Try the chef's special, it's amazing!",
                    "Best time to visit is weekday afternoons.",
                    "Parking can be difficult, use the side street.",
                    "Make sure to make a reservation on weekends.",
                    "The happy hour deals are great value.",
                    "Don't order the fish, stick with the steak.",
                ]),
                "date": f"202{random.randint(0,3)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "compliment_count": random.randint(0, 10),
            }
            f.write(json.dumps(tip) + "\n")
    print(f"  Done: {n} records")


def generate_users(n=20000):
    """Generate sample user data."""
    filepath = os.path.join(RAW_DATA_DIR, "yelp_academic_dataset_user.json")
    print(f"Generating {n} users -> {filepath}")
    with open(filepath, "w", encoding="utf-8") as f:
        for i in range(n):
            user = {
                "user_id": f"u{i:06d}",
                "name": f"User_{random.randint(1000, 9999)}",
                "review_count": random.randint(0, 500),
                "yelping_since": f"201{random.randint(0,9)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "useful": random.randint(0, 1000),
                "funny": random.randint(0, 500),
                "cool": random.randint(0, 500),
                "elite": ",".join(str(y) for y in random.sample(range(2010, 2025), random.randint(0, 5))),
                "friends": "",
                "fans": random.randint(0, 100),
                "average_stars": round(random.uniform(1.0, 5.0), 2),
                "compliment_hot": random.randint(0, 50),
                "compliment_more": random.randint(0, 50),
                "compliment_profile": random.randint(0, 50),
                "compliment_cute": random.randint(0, 50),
            }
            f.write(json.dumps(user) + "\n")
    print(f"  Done: {n} records")


if __name__ == "__main__":
    print("=" * 50)
    print("Generating sample Yelp-format data")
    print("=" * 50)
    generate_businesses(5000)
    generate_reviews(20000)
    generate_checkins(20000)
    generate_tips(20000)
    generate_users(20000)
    print("\nAll sample data generated!")
