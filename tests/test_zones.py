import unittest

from core.zones import Zone, next_zone, zone_address


class ZoneTests(unittest.TestCase):
    def test_zone_select_cycles_front_rear_left_right(self):
        seen, zone = [], Zone.FRONT
        for _ in range(4):
            zone = next_zone(zone)
            seen.append(zone)
        self.assertEqual(seen, [Zone.REAR, Zone.LEFT, Zone.RIGHT, Zone.FRONT])

    def test_zone_addresses_match_the_ip_plan(self):
        self.assertEqual([zone_address("192.168.10", zone) for zone in Zone],
                         ["192.168.10.11", "192.168.10.12", "192.168.10.13", "192.168.10.14"])
