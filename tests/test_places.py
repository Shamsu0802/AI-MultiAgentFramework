from dotenv import load_dotenv

from app.tools.geoapify_tool import GeoapifyTool


load_dotenv()


tool = GeoapifyTool()


# Ooty approximate coordinates
latitude = 11.4064
longitude = 76.6932


places = tool.search_places(
    latitude=latitude,
    longitude=longitude,
    category="tourism",
    radius=5000,
    limit=10
)


print("\nPlaces found:\n")

for place in places:

    print(
        f"Name: {place['name']}"
    )

    print(
        f"Address: {place['address']}"
    )

    print(
        f"Location: "
        f"{place['latitude']}, "
        f"{place['longitude']}"
    )

    print(
        f"Categories: "
        f"{place['categories']}"
    )

    print("-" * 50)