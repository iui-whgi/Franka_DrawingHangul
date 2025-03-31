import os, json

# korean.json 열기
script_path = os.path.abspath(__file__)
json_path = os.path.dirname(script_path)
json_path += "/asset/korean.json"
with open(json_path, encoding="utf-8") as f:
    data = json.load(f)


def find_by_name(character_name, key):
    """json에서 받은 정보를 분리하는 함수
    Args:
        character_name: 찾을 한글 문자 한 개
        key (string): dictionary의 키 "path", "kind"
    Returns:
        "path":
            list: dictionary("start", "end")
        "kind":
            list: [자음 모음, (모음 종류)]
    """
    for character in data["characters"]:
        if character["name"] == character_name:
            return character[key]
    return None

def get_coordinate(i):
    """stroke 정보를 좌표 리스트로 바꾸는 함수
    Args:
        i: path list의 한 요소(dictionary). 한 획.
    Returns:
        list: ["start" 좌표, "end" 좌표]
    """
    return [
        [i["start"][0], i["start"][1], i["start"][2]],
        [i["end"][0], i["end"][1], i["end"][2]],
    ]


def splitCharacter(a) -> list:
    """한글 한 글자의 자음, 모음 받침을 분리하는 함수
    Args:
        a: 분리할 한글 문자 한 개
    Returns:
        list: [자음, 모음, (받침)]
            자음 한 개 혹은 모음 한 개일 경우 그 문자 하나 든 리스트
            받침이 없을 경우 [자음, 모음]
    """
    a = int(ord(a))
    son = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', "ㅃ", 
           'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    mom = ['ㅏ','ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 
           'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 
           'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
    support = ['ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 
               'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 
               'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    arr = []
    if a >= ord('가'):
        a -= ord('가')
        arr.append(son[a // (len(mom) * (len(support) + 1))])
        a %= len(mom) * (len(support) + 1)
        arr.append(mom[a // (len(support) + 1)])
        a %= len(support) + 1
        if a:
            arr.append(support[a - 1])
    else:
        arr.append(chr(a))

    return arr


def makeStrokes(a) -> list:
    """한글 한 글자의 자음, 모음 받침을 스케일링하고 결합하는 함수
    Args:
        a: 그릴 한글 문자 한 개
    Returns:
        list: 한글 한 글자를 그리기 위한 획 리스트
    """
    characters = splitCharacter(a)
    strokes = []
    
    if len(characters) == 1:
        stroke = find_by_name(characters[0], "path")
        for i in stroke:
            strokes.append(get_coordinate(i))
    
    elif len(characters) == 2:
        kind_info = find_by_name(characters[1], "kind")
        
        if kind_info is None:
            print(f"Warning: No kind info for '{characters[1]}'")
            return strokes
        
        elif kind_info[1] == 0:
            stroke = find_by_name(characters[0], "path")
            for i in stroke:
                strokes.append(get_coordinate(i))
            for i in strokes:
                i[0][1] = i[0][1] * 0.6
                i[1][1] = i[1][1] * 0.6
                i[0][2] = i[0][2] * 0.8 + 0.02
                i[1][2] = i[1][2] * 0.8 + 0.02
                
            # 중성 이동 적용 (예외 처리 추가)
            stroke = find_by_name(characters[1], "path")
            for i in stroke:
                strokes.append(get_coordinate(i))
        
        elif kind_info[1] == 1:
            stroke = find_by_name(characters[0], "path")
            for i in stroke:
                strokes.append(get_coordinate(i))
            for i in strokes:
                i[0][1] = i[0][1] * 0.8 + 0.02
                i[1][1] = i[1][1] * 0.8 + 0.02
                i[0][2] = i[0][2] * 0.6 + 0.06
                i[1][2] = i[1][2] * 0.6 + 0.06
            
            # 중성 이동 적용 (예외 처리 추가)
            stroke = find_by_name(characters[1], "path")
            for i in stroke:
                strokes.append(get_coordinate(i))
    
    elif len(characters) == 3:
        kind_info = find_by_name(characters[1], "kind")
        
        if kind_info is None:
            print(f"Warning: No kind info for '{characters[1]}'")
            return strokes
        
        elif kind_info[1] == 0:
            stroke = find_by_name(characters[0], "path")
            for i in stroke:
                strokes.append(get_coordinate(i))
            for i in strokes:
                i[0][1] = i[0][1] * 0.6
                i[1][1] = i[1][1] * 0.6
                i[0][2] = i[0][2] * 0.8 + 0.02
                i[1][2] = i[1][2] * 0.8 + 0.02
                
            # 중성 이동 적용 (예외 처리 추가)
            stroke = find_by_name(characters[1], "path")
            for i in stroke:
                strokes.append(get_coordinate(i))
        
        elif kind_info[1] == 1:
            stroke = find_by_name(characters[0], "path")
            for i in stroke:
                strokes.append(get_coordinate(i))
            for i in strokes:
                i[0][1] = i[0][1] * 0.8 + 0.02
                i[1][1] = i[1][1] * 0.8 + 0.02
                i[0][2] = i[0][2] * 0.6 + 0.06
                i[1][2] = i[1][2] * 0.6 + 0.06
            
            # 중성 이동 적용 (예외 처리 추가)
            stroke = find_by_name(characters[1], "path")
            for i in stroke:
                strokes.append(get_coordinate(i))
        
        for i in strokes:
            i[0][2] = i[0][2] * 0.65 + 0.07
            i[1][2] = i[1][2] * 0.65 + 0.07
        
        _strokes = []
        stroke = find_by_name(characters[2], "path")
        for i in stroke:
            _strokes.append(get_coordinate(i))
        for i in _strokes:
            i[0][1] = i[0][1] * 0.8 + 0.02
            i[1][1] = i[1][1] * 0.8 + 0.02
            i[0][2] = i[0][2] * 0.35
            i[1][2] = i[1][2] * 0.35
        strokes.extend(_strokes)

    dict = []
    for i in range(len(strokes)):
        dict.append({"start": strokes[i][0], "end": strokes[i][1]})
    return dict


def scale(stroke, y, z) -> None:
    """글자 크기를 조절하는 함수
    Args:
        stroke: 스케일링 할 획 리스트
        y: y축 스케일
        z: z축 스케일
    """
    for i in stroke:
        i[0][1] = i[0][1] * y
        i[1][1] = i[1][1] * y
        i[0][2] = i[0][2] * z
        i[1][2] = i[1][2] * z
    return


def move(a, m) -> list:
    """한글 한 글자씩 translate하는 함수
    Args:
        a: 옮길 한글 글자 한 개
        m (list): 옮길 양(y, z)
    Returns:
        list: 해당 글자의 모든 획
    """
    _strokes = []
    stroke = makeStrokes(a)
    for i in stroke:
        _strokes.append(get_coordinate(i))
    for i in _strokes:
        i[0][1] = i[0][1] + m[0]
        i[1][1] = i[1][1] + m[0]
        i[0][2] = i[0][2] + m[1]
        i[1][2] = i[1][2] + m[1]
    return _strokes


def makeStrings(list) -> dict:
    """한글 한 글자의 자음, 모음 받침을 분리하는 함수
    Args:
        list: 출력할 한글 문자열
    Returns:
        dict: 문자열을 합친 모든 획
    """
    k = 0.18    # 글자 한 칸 가로, 세로 길이
    # 글자 배치
    c = [
        [-k * 3, 0.0], [-k * 2, 0.0], [-k, 0.0], 
        [0.0, 0.0], [k, 0.0], [k * 2, 0.0], 
        [-k * 3, -0.21], [-k * 2, -k], [-k, -k]
    ]
    strokes = []
    for i in range(len(list)):
        strokes.extend(move(list[i], c[i]))
    scale(strokes, 0.7, 0.7)
    dict = []
    for i in range(len(strokes)):
        dict.append({"start": strokes[i][0], "end": strokes[i][1]})
    return dict