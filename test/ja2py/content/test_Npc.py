import unittest
from ja2py.content.Npc import NpcData, NPC_RECORD_LENGTH, read_uint, read_int, _format_fact, _format_quest, _format_flags


class TestNpcData(unittest.TestCase):
    def test_constructor_all_zeros(self):
        # Test with a 32-byte string of all zeros
        zero_bytes = b'\x00' * NPC_RECORD_LENGTH
        npc_data = NpcData(zero_bytes)

        expected_data = {
            'ubIdentifier': 0,
            'fFlags': '0000000000000000',
            'usFactMustBeTrue': '0',
            'usFactMustBeFalse': '0',
            'ubQuest': '0',
            'ubFirstDay': 0,
            'ubLastDay': 0,
            'ubApproachRequired': 0,
            'ubOpinionRequired': 0,
            'ubQuoteNum': 0,
            'ubNumQuotes': 0,
            'ubStartQuest': '0',
            'ubEndQuest': '0',
            'ubTriggerNPC': 0,
            'ubTriggerNPCRec': 0,
            'usSetFactTrue': '0',
            'usGiftItem': 0,
            'usGoToGridno': 0,
            'sActionData': 0,
            'sRequiredItem': 'NOTHING',
            'sRequiredGridno': 'N/A'
        }
        self.assertDictEqual(npc_data.data, expected_data)

    def test_pretty_print(self):
        # Ensure pretty_print runs without errors
        zero_bytes = b'\x00' * NPC_RECORD_LENGTH
        npc_data = NpcData(zero_bytes)
        try:
            npc_data.pretty_print()
        except Exception as e:
            self.fail(f"pretty_print raised an exception: {e}")

    def test_constructor_various_values(self):
        # A sample byte string to test various fields
        # This byte string is manually crafted to trigger different parsing scenarios
        # Bytes:
        # 0-1: fFlags (e.g., 0x0100 -> 0000000100000000)
        # 2-3: sRequiredItem/sRequiredGridno (e.g., 0x0001 -> '1', 0xFFFF -> '-1')
        # 4-5: usFactMustBeTrue (e.g., 0x0100 -> '256')
        # 6-7: usFactMustBeFalse (e.g., 0xFFFF -> 'NO_FACT')
        # 8: ubQuest (e.g., 0xFF -> 'NO_QUEST')
        # 9: ubFirstDay (e.g., 0x05 -> '5')
        # 10: ubLastDay (e.g., 0x0A -> '10')
        # 11: ubApproachRequired (e.g., 0x01 -> '1')
        # 12: ubOpinionRequired (e.g., 0x02 -> '2')
        # 13: ubQuoteNum (e.g., 0x03 -> '3')
        # 14: ubNumQuotes (e.g., 0x04 -> '4')
        # 15: ubStartQuest (e.g., 0x01 -> '1')
        # 16: ubEndQuest (e.g., 0x02 -> '2')
        # 17: ubTriggerNPC (e.g., 0x01 -> '1')
        # 18: ubTriggerNPCRec (e.g., 0x02 -> '2')
        # 19: (padding byte)
        # 20-21: usSetFactTrue (e.g., 0x0100 -> '256')
        # 22: usGiftItem (e.g., 0x07 -> '7')
        # 23: (padding byte)
        # 24-25: usGoToGridno (e.g., 0x0100 -> '256')
        # 26-27: sActionData (e.g., 0x0100 -> '256')
        # 28-31: (padding bytes)

        test_bytes = bytearray(NPC_RECORD_LENGTH)
        test_bytes[0:2] = b'\x00\x01' # fFlags = 0x0100 -> 0000000100000000 (little endian: 0x00 then 0x01)
        test_bytes[2:4] = b'\x01\x00' # sRequiredItem = 1 (positive value)
        test_bytes[4:6] = b'\x00\x01' # usFactMustBeTrue = 256
        test_bytes[6:8] = b'\xff\xff' # usFactMustBeFalse = 65535 (NO_FACT)
        test_bytes[8] = 0xff      # ubQuest = 255 (NO_QUEST)
        test_bytes[9] = 0x05      # ubFirstDay = 5
        test_bytes[10] = 0x0a     # ubLastDay = 10
        test_bytes[11] = 0x01     # ubApproachRequired = 1
        test_bytes[12] = 0x02     # ubOpinionRequired = 2
        test_bytes[13] = 0x03     # ubQuoteNum = 3
        test_bytes[14] = 0x04     # ubNumQuotes = 4
        test_bytes[15] = 0x01     # ubStartQuest = 1
        test_bytes[16] = 0x02     # ubEndQuest = 2
        test_bytes[17] = 0x01     # ubTriggerNPC = 1
        test_bytes[18] = 0x02     # ubTriggerNPCRec = 2
        test_bytes[20:22] = b'\x00\x01' # usSetFactTrue = 256
        test_bytes[22] = 0x07     # usGiftItem = 7
        test_bytes[24:26] = b'\x00\x01' # usGoToGridno = 256
        test_bytes[26:28] = b'\x00\x01' # sActionData = 256 (signed int)

        npc_data = NpcData(bytes(test_bytes))

        expected_data = {
            'ubIdentifier': 0,
            'fFlags': '0000000100000000',
            'usFactMustBeTrue': '256',
            'usFactMustBeFalse': 'NO_FACT',
            'ubQuest': 'NO_QUEST',
            'ubFirstDay': 5,
            'ubLastDay': 10,
            'ubApproachRequired': 1,
            'ubOpinionRequired': 2,
            'ubQuoteNum': 3,
            'ubNumQuotes': 4,
            'ubStartQuest': '1',
            'ubEndQuest': '2',
            'ubTriggerNPC': 1,
            'ubTriggerNPCRec': 2,
            'usSetFactTrue': '256',
            'usGiftItem': 7,
            'usGoToGridno': 256,
            'sActionData': 256,
            'sRequiredItem': '1',
            'sRequiredGridno': 'N/A'
        }
        self.assertDictEqual(npc_data.data, expected_data)

    def test_s_required_item_and_gridno_negative(self):
        # Test sRequiredItem and sRequiredGridno with a negative value
        test_bytes = bytearray(NPC_RECORD_LENGTH)
        test_bytes[2:4] = b'\xff\xff' # -1 as signed int (little endian)

        npc_data = NpcData(bytes(test_bytes))

        self.assertEqual(npc_data.data['sRequiredItem'], 'NOTHING')
        self.assertEqual(npc_data.data['sRequiredGridno'], '1') # Absolute value of -1

    def test_s_required_item_and_gridno_zero(self):
        # Test sRequiredItem and sRequiredGridno with zero value
        test_bytes = bytearray(NPC_RECORD_LENGTH)
        test_bytes[2:4] = b'\x00\x00' # 0 as signed int (little endian)

        npc_data = NpcData(bytes(test_bytes))

        self.assertEqual(npc_data.data['sRequiredItem'], 'NOTHING')
        self.assertEqual(npc_data.data['sRequiredGridno'], 'N/A')

    def test_read_uint(self):
        self.assertEqual(read_uint(b'\x01'), 1)
        self.assertEqual(read_uint(b'\x01\x00'), 1)
        self.assertEqual(read_uint(b'\xff\x00'), 255)
        self.assertEqual(read_uint(b'\xff\xff'), 65535)

    def test_read_int(self):
        self.assertEqual(read_int(b'\x01'), 1)
        self.assertEqual(read_int(b'\x01\x00'), 1)
        self.assertEqual(read_int(b'\xff\x00'), 255)
        self.assertEqual(read_int(b'\xff\x7f'), 32767) # Max signed short
        self.assertEqual(read_int(b'\x00\x80'), -32768) # Min signed short
        self.assertEqual(read_int(b'\xff\xff'), -1)

    def test_format_fact(self):
        self.assertEqual(_format_fact(65535), 'NO_FACT')
        self.assertEqual(_format_fact(123), '123')
        self.assertEqual(_format_fact(0), '0')

    def test_format_quest(self):
        self.assertEqual(_format_quest(255), 'NO_QUEST')
        self.assertEqual(_format_quest(10), '10')
        self.assertEqual(_format_quest(0), '0')

    def test_format_flags(self):
        self.assertEqual(_format_flags(b'\x00\x00'), '0000000000000000')
        self.assertEqual(_format_flags(b'\x01\x00'), '0000000000000001')
        self.assertEqual(_format_flags(b'\xff\x00'), '0000000011111111')
        self.assertEqual(_format_flags(b'\x00\x01'), '0000000100000000')
        self.assertEqual(_format_flags(b'\xff\xff'), '1111111111111111')


if __name__ == '__main__':
    unittest.main()
