"""법령센터 XML 파싱의 비표준 엔티티 내성 회귀 테스트.

법령센터가 검색어를 응답에 그대로 echo 하면서 가운뎃점(·)을 &middot; 같은
XML 비표준 엔티티로 돌려줘 파싱이 깨지던 버그를 고정한다.
"""
import unittest
import xml.etree.ElementTree as ET

from app.clients import law_client


class FromStringEntityTest(unittest.TestCase):
    def test_middot_entity_does_not_crash(self):
        # 표준 ET.fromstring 은 &middot; 에서 ParseError 를 낸다.
        bad = '<OrdinSearch><키워드>의료&middot;복지</키워드></OrdinSearch>'
        with self.assertRaises(ET.ParseError):
            ET.fromstring(bad)
        # 관대한 파서는 통과해야 한다.
        root = law_client._fromstring(bad)
        self.assertEqual(root.tag, "OrdinSearch")

    def test_valid_entities_preserved(self):
        root = law_client._fromstring("<a>1 &amp; 2 &lt; 3</a>")
        self.assertEqual(root.text, "1 & 2 < 3")


if __name__ == "__main__":
    unittest.main()
