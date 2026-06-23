from openlocationcode import openlocationcode as olc

print("C97V+MPF near Sakon Nakhon:", olc.decode(olc.recoverNearest("C97V+MPF", 17.4, 104.4)).latitudeCenter, olc.decode(olc.recoverNearest("C97V+MPF", 17.4, 104.4)).longitudeCenter)
print("7WP8+JQ8 near Sakon Nakhon:", olc.decode(olc.recoverNearest("7WP8+JQ8", 17.4, 104.4)).latitudeCenter, olc.decode(olc.recoverNearest("7WP8+JQ8", 17.4, 104.4)).longitudeCenter)
