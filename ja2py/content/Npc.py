NPC_RECORD_LENGTH = 32


class NpcData(object):
    def __init__(self, bytes):
        ## TODO: support RUSSIAN version
        data = {}
        data['ubIdentifier'] = 0
        data['fFlags'] = _format_flags(bytes[0:2])
        data['usFactMustBeTrue'] = _format_fact(read_uint(bytes[4:6]))
        data['usFactMustBeFalse'] = _format_fact(read_uint(bytes[6:8]))
        data['ubQuest'] = _format_quest(read_uint([bytes[8]]))
        data['ubFirstDay'] = read_uint([bytes[9]])
        data['ubLastDay'] = read_uint([bytes[10]])
        data['ubApproachRequired'] = read_uint([bytes[11]])
        data['ubOpinionRequired'] = read_uint([bytes[12]])
        data['ubQuoteNum'] = read_uint([bytes[13]])
        data['ubNumQuotes'] = read_uint([bytes[14]])
        data['ubStartQuest'] = _format_quest(read_uint([bytes[15]]))
        data['ubEndQuest'] = _format_quest(read_uint([bytes[16]]))
        data['ubTriggerNPC'] = read_uint([bytes[17]])
        data['ubTriggerNPCRec'] = read_uint([bytes[18]])
        data['usSetFactTrue'] = _format_fact(read_uint(bytes[20:22]))
        data['usGiftItem'] = read_uint(bytes[22:23])
        data['usGoToGridno'] = read_uint(bytes[24:26])
        data['sActionData'] = read_int(bytes[26:28])

        r = read_int(bytes[2:4])
        data['sRequiredItem'] = str(r) if r > 0 else 'NOTHING'
        data['sRequiredGridno'] = str(-r) if r < 0 else 'N/A'
        self._data = data

    @property
    def data(self):
        return self._data

    def pretty_print(self):
        print("""========================================
  fFlags:                {fFlags}
  sRequiredItem:         {sRequiredItem}
  sRequiredGridno:       {sRequiredGridno}
  usFactMustBeTrue:      {usFactMustBeTrue}
  usFactMustBeFalse:     {usFactMustBeFalse}
  ubQuest:               {ubQuest}
  ubFirstDay :           {ubFirstDay}
  ubLastDay:             {ubLastDay}
  ubApproachRequired:    {ubApproachRequired}
  ubOpinionRequired:     {ubOpinionRequired}
  ubQuoteNum:            {ubQuoteNum}
  ubNumQuotes:           {ubNumQuotes}
  ubStartQuest:          {ubStartQuest}
  ubEndQuest:            {ubEndQuest}
  ubTriggerNPC:          {ubTriggerNPC}
  ubTriggerNPCRec:       {ubTriggerNPCRec}
  usSetFactTrue:         {usSetFactTrue}
  usGiftItem:            {usGiftItem}
  usGoToGridno:          {usGoToGridno}
  sActionData:           {sActionData}
""".format(**self._data))


def read_uint(bytes):
    return int.from_bytes(bytes, byteorder='little', signed=False)


def read_int(bytes):
    return int.from_bytes(bytes, byteorder='little', signed=True)


def _format_fact(fact_num):
    if fact_num == 65535:
        return 'NO_FACT'
    return str(fact_num)


def _format_quest(quest):
    if quest == 255:
        return 'NO_QUEST'
    return str(quest)


def _format_flags(bytes):
    flags_len = len(bytes) * 8
    return '{:b}'.format(read_uint(bytes)).rjust(flags_len, '0')
