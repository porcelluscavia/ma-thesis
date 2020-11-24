import os
import re

PHON = True
MIN_WORDS_PER_UTTERANCE = 3

DATA_DIR = './data/'
if PHON:
    INPUT_DIR = DATA_DIR + 'ndc_phon_with_informant_codes/files/'
    OUT_FILE = DATA_DIR + 'phon_parsed.tsv'
    LOG_FILE = DATA_DIR + 'phon_log.txt'
else:
    INPUT_DIR = DATA_DIR + 'ndc_with_informant_codes/files/'
    OUT_FILE = DATA_DIR + 'bokmaal_parsed.tsv'
    LOG_FILE = DATA_DIR + 'bokmaal_log.txt'


# pre-reform counties

nord_norge = {'finnmark': ['hammerfest', 'kautokeino', 'kirkenes',
                             'kjoellefjord', 'lakselv', 'tana', 'vardoe'],
                'nordland': ['ballangen', 'beiarn', 'bodoe', 'hattfjelldal',
                             'heroeyN', 'mo_i_rana', 'myre', 'narvik', 'stamsund',
                             'steigen', 'soemna'],
                'troms': ['botnhamn', 'karlsoey', 'kirkesdalen', 'kvaefjord',
                        'kvaenangen', 'kaafjord', 'lavangen', 'medby',
                        'mefjordvaer', 'stonglandseidet','tromsoe']}
# TODO check if any of these are in Indre Troms and should be moved to soernorsk

soerlandet = {'aust_agder': ['evje', 'landvik', 'valle', 'vegaarshei'],
                'vest_agder': ['kristiansand', 'lyngdal', 'sirdal', 'vennesla',
                             'aaseral']}

troendelag = {'nord_troendelag': ['inderoey', 'lierne', 'meraaker', 'namdalen'],
                'soer_troendelag': ['bjugn', 'gauldal', 'oppdal', 'roeros',
                                    'selbu', 'skaugdalen', 'stokkoeya',
                                    'trondheim']}

vestlandet = {'hordaland': ['bergen', 'boemlo', 'eidfjord', 'fusa',
                            'kvinnherad', 'lindaas', 'voss'],
                'moere_og_romsdal': ['aure', 'bud', 'heroeyMR', 'rauma',
                                     'stranda', 'surnadal', 'todalen', 'volda'],
                'rogaland': ['gjesdal', 'hjelmeland', 'karmoey', 'sokndal',
                             'stavanger', 'suldal', 'time'],
                'sogn_og_fjordane': ['hyllestad', 'joelster', 'kalvaag', 'luster',
                                     'stryn']}
oestlandet = {'akershus': ['enebakk', 'lommedalen', 'nes'],
                'buskerud': ['darbu', 'flaa', 'rollag', 'sylling', 'aal'],
                'hedmark': ['alvdal', 'dalsbygda', 'drevsjoe', 'kirkenaer',
                            'rena', 'stange', 'trysil'],
                'oppland': ['brekkom', 'gausdal', 'jevnaker', 'kvam', 'lom',
                            'skreia', 'vang', 'vestre_slidre'],
                'telemark': ['hjartdal', 'langesund', 'nissedal', 'tinn',
                             'vinje'],
                'vestfold': ['brunlanes', 'hof', 'lardal'],
                'oestfold': ['aremark', 'fredrikstad', 'roemskog']}

# The dialect area division is based on Mæhlum & Røyneland: Det norske dialektlandskapet
vestnorsk = {}
for k in vestlandet:
    vestnorsk[k] = vestlandet[k]
for k in soerlandet:
    vestnorsk[k] = soerlandet[k]
norwegian = {'nordnorsk': nord_norge,
             'troendersk': troendelag,
             'vestnorsk': vestnorsk,
             'oestnorsk': oestlandet}
norwegian_places = []
place2county = {}
place2area = {}
for dialect_area in norwegian:
    for county in norwegian[dialect_area]:
        for place in norwegian[dialect_area][county]:
            norwegian_places.append(place)
            place2area[place] = dialect_area
            place2county[place] = county



skip_tokens = ['#', '##',  # pauses
                 '*',  # overlapping utterances
                 'e',  # TODO: 'e' only in bokmål version
                 '?', '!', '"', '...', '…',
                 # "Interjeksjonar vi ikkje endrar stavemåten på"
                 'ee', 'eh', 'ehe', 'em', 'heh', 'hm', 'm', 'm-m', 'mhm', 'mm'
                ]
# TODO what about ja, nei, og

def is_named_entity(string):
    # Names: F1 (F2, F3, ...), M1, E1
    # Other NEs: N1
    # Names of interview participants use the participant code, which contains a number.
    return bool(re.search(r'\d', string))

places = set()
informants = set()
_, _, filenames = next(os.walk(INPUT_DIR))
with open(OUT_FILE, 'w', encoding='utf8') as out_file:
    for file in filenames:
        place = file.split('_')[0]
        if place not in norwegian_places:
            continue
        places.add(place)
        with open(INPUT_DIR + file, 'r', encoding='utf8') as in_file:
            for line in in_file:
                line = line.strip()
                tokens = line.split(' ')
                speaker = tokens[0]
                if not speaker.startswith(place):
                    # Interviewer, not informant
                    # TODO check if there is information on where the interviewers are from
                    continue
                informants.add(speaker)
                utterance = []
                for token in tokens[1:]:
                    if token.endswith('-'):
                        continue
                    if token in skip_tokens:
                        continue
                    if is_named_entity(token):
                        continue
                    token = token.replace('_', '')
                    if len(token) > 0 and token[0].islower():
                        # Capitalization check to exclude place names
                        utterance.append(token)
                if len(utterance) < MIN_WORDS_PER_UTTERANCE:
                    continue
                utterance = ' '.join(utterance).strip()
                out_file.write(place2area[place] + '\t' + place2county[place] + '\t' + place + '\t' + file + '\t' + utterance + '\n')

with open(LOG_FILE, 'w', encoding='utf8') as log_file:
    log_file.write('No. of places: ' + str(len(places)))
    log_file.write('\n')
    log_file.write(str(places))
    log_file.write('\n\n')
    log_file.write('No. of informants: ' + str(len(informants)))
    log_file.write('\n')
    log_file.write(str(informants))
    log_file.write('\n')
    
    