from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="fonmayang_debug")
location = geolocator.reverse("17.4142, 104.3943", language='th')
print(location.address)
