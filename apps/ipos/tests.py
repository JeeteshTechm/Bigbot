import re
import typing

import pytest


def clean_text(string: str) -> str:
    """Removes punctuation, extra spaces, and lowercases a string."""
    import re

    f = filter(lambda c: c.isalnum() or c.isspace() or c in ["-", "_"], string.strip().lower())
    res = "".join(f)
    res = re.sub(r"\s\s+", " ", res)
    res = re.sub(r"\t", " ", res)
    res = re.sub(r"\n", " ", res)
    return res


def fuzzy_search(needle: str, hay: str) -> typing.Tuple[float, str]:
    """Fuzzy search needle in hay.
    Args:
        needle (str): String to look for.
        hay (str): String to look into.

    Returns:
        Tuple[float, str]: A tuple with two values, the first value is float 0 and 1 where 0 means
            that no similar string to the needle was found, and 1 means a perfect match. The second
            value is the substring found.
    """
    from textdistance import levenshtein

    hay = clean_text(hay)
    hay_length = len(hay)
    needle = clean_text(needle)
    needle_length = len(needle)

    if needle_length > hay_length:
        needle = needle[:hay_length]

    position = 0
    similarity = 0
    for i in range(hay_length):
        if i + needle_length > hay_length:
            break
        substring = hay[i : i + needle_length]
        tmp_similarity = levenshtein.normalized_similarity(needle.lower(), substring.lower())
        if tmp_similarity > similarity:
            position = i
            similarity = tmp_similarity

    if similarity == 0:
        return 0.0, ""
    return similarity, hay[position : position + needle_length]


field_regex = re.compile(r"^(?P<object_name>.+)_(?P<index>\d+)_(?P<field_name>.+)$")
id_regex = re.compile(r"^_.*$")

meta = {
    "_edit_lock": "1616136129:2",
    "_edit_last": "2",
    "logo": "388",
    "_logo": "field_6032268135bea",
    "tagline": "",
    "_tagline": "field_6032268935beb",
    "introduction": "IPOS International is a wholly-owned subsidiary of the Intellectual Property Office of Singapore (IPOS), housing over 100 IP experts in areas such as IP strategy and management, patent search and analysis, and IP education and training.\r\n\r\nAs the expertise and enterprise engagement arm of IPOS, our focus is on helping enterprises and industries use IP and intangible assets for business growth.\r\n\r\nOur ambition is to be the Global Centre of Excellence for intangible assets, anchoring Singapore as a hub for global innovation flows. We aim to use our expertise, partnerships and networks in the innovation ecosystem worldwide to bridge possibilities for intangible asset-rich enterprises and industries seeking to grow.",
    "_introduction": "field_6032269235bec",
    "ip_services_focus_percentage": "100",
    "_ip_services_focus_percentage": "field_6032275a35bed",
    "ip_services_focus_list_0_ip_services_focus": "IP Strategy Consultancy",
    "_ip_services_focus_list_0_ip_services_focus": "field_603227ab35bef",
    "ip_services_focus_list_1_ip_services_focus": "Patent Analytics",
    "_ip_services_focus_list_1_ip_services_focus": "field_603227ab35bef",
    "ip_services_focus_list_2_ip_services_focus": "IP Training",
    "_ip_services_focus_list_2_ip_services_focus": "field_603227ab35bef",
    "ip_services_focus_list_3_ip_services_focus": "IP Portfolio Management",
    "_ip_services_focus_list_3_ip_services_focus": "field_603227ab35bef",
    "ip_services_focus_list": "4",
    "_ip_services_focus_list": "field_6032279735bee",
    "client_demographics_list_0_client_demographics": "Small Enterprise (Revenue Less than 10mln)​",
    "_client_demographics_list_0_client_demographics": "field_6049bdf62d577",
    "client_demographics_list_0_percentage": "10",
    "_client_demographics_list_0_percentage": "field_6049be8c2b0d8",
    "client_demographics_list_1_client_demographics": "Medium Enterprise  (Revenue $10mln to $100mln)​",
    "_client_demographics_list_1_client_demographics": "field_6049bdf62d577",
    "client_demographics_list_1_percentage": "15",
    "_client_demographics_list_1_percentage": "field_6049be8c2b0d8",
    "client_demographics_list_2_client_demographics": "Government",
    "_client_demographics_list_2_client_demographics": "field_6049bdf62d577",
    "client_demographics_list_2_percentage": "70",
    "_client_demographics_list_2_percentage": "field_6049be8c2b0d8",
    "client_demographics_list_3_client_demographics": "Others",
    "_client_demographics_list_3_client_demographics": "field_6049bdf62d577",
    "client_demographics_list_3_percentage": "5",
    "_client_demographics_list_3_percentage": "field_6049be8c2b0d8",
    "client_demographics_list": "4",
    "_client_demographics_list": "field_6032283c35bf1",
    "profile_views": "",
    "_profile_views": "field_603229328ef98",
    "minimum_project_size": "10000",
    "_minimum_project_size": "field_6032293b8ef99",
    "average_hourly_rate": "$-$$$",
    "_average_hourly_rate": "field_603229438ef9a",
    "size_of_total_employees": "101-200",
    "_size_of_total_employees": "field_6032294a8ef9b",
    "year_of_establishment": "2014",
    "_year_of_establishment": "field_603229558ef9c",
    "key_office_presence_in_sg": "Paya Lebar",
    "_key_office_presence_in_sg": "field_6032295b8ef9d",
    "ip_expertises_list_0_ip_expertise": "6",
    "_ip_expertises_list_0_ip_expertise": "field_6049bf356982d",
    "ip_expertises_list_1_ip_expertise": "22",
    "_ip_expertises_list_1_ip_expertise": "field_6049bf356982d",
    "ip_expertises_list_2_ip_expertise": "7",
    "_ip_expertises_list_2_ip_expertise": "field_6049bf356982d",
    "ip_expertises_list_3_ip_expertise": "17",
    "_ip_expertises_list_3_ip_expertise": "field_6049bf356982d",
    "ip_expertises_list": "4",
    "_ip_expertises_list": "field_60322a8005775",
    "market_served_list_0_market": "Singapore",
    "_market_served_list_0_market": "field_6049c24873f92",
    "market_served_list_1_market": "China",
    "_market_served_list_1_market": "field_6049c24873f92",
    "market_served_list_2_market": "Qatar",
    "_market_served_list_2_market": "field_6049c24873f92",
    "market_served_list": "3",
    "_market_served_list": "field_60322abf05778",
    "industry_focus_list_0_focus": "Precision Engineering",
    "_industry_focus_list_0_focus": "field_6049c3a99cf0f",
    "industry_focus_list_1_focus": "Professional Services",
    "_industry_focus_list_1_focus": "field_6049c3a99cf0f",
    "industry_focus_list_2_focus": "ICT and Media",
    "_industry_focus_list_2_focus": "field_6049c3a99cf0f",
    "industry_focus_list_3_focus": "Healthcare",
    "_industry_focus_list_3_focus": "field_6049c3a99cf0f",
    "industry_focus_list_4_focus": "Food Manufacturing",
    "_industry_focus_list_4_focus": "field_6049c3a99cf0f",
    "industry_focus_list_5_focus": "Financial Services",
    "_industry_focus_list_5_focus": "field_6049c3a99cf0f",
    "industry_focus_list": "6",
    "_industry_focus_list": "field_60322ad60577a",
    "key_practice_experts_0_name": "Dixon Soh",
    "_key_practice_experts_0_name": "field_60322b670577d",
    "key_practice_experts_0_profile_pic": "",
    "_key_practice_experts_0_profile_pic": "field_60322b6b0577e",
    "key_practice_experts_0_job_title": "Deputy Director, IP Strategy Solutions",
    "_key_practice_experts_0_job_title": "field_60322b860577f",
    "key_practice_experts_0_bio": "Dixon has practised law as a private practitioner, in-house legal counsel and now as a lawyer in the public sector.  Over the years, he has advised numerous entities including MNCs and SMEs across many different industries, such as IT, e-commerce, FinTech and media.  Dixon is very familiar with the challenges experienced by businesses throughout South East Asia, Australia and New Zealand.\r\n\r\nPrior to joining public service, Dixon was serving one of the fastest growing ‘Unicorn’ in Southeast Asia as an in-house legal counsel specialising in the area of IP and commercial dispute resolution.\r\n\r\nDixon is a graduate of the University of Tasmania and holds qualifications to practise law in Singapore, Australia and New Zealand. Dixon has recently been acknowledged in IAM Strategy 300 rankings.",
    "_key_practice_experts_0_bio": "field_60322b9605780",
    "key_practice_experts_0_awards_list_0_award": "IAM 300",
    "_key_practice_experts_0_awards_list_0_award": "field_60322ba905782",
    "key_practice_experts_0_awards_list_1_award": "RMC",
    "_key_practice_experts_0_awards_list_1_award": "field_60322ba905782",
    "key_practice_experts_0_awards_list": "2",
    "_key_practice_experts_0_awards_list": "field_60322b9d05781",
    "key_practice_experts_0_special_mentions_list": "",
    "_key_practice_experts_0_special_mentions_list": "field_60322bb205783",
    "key_practice_experts_1_name": "Fu Zhikang",
    "_key_practice_experts_1_name": "field_60322b670577d",
    "key_practice_experts_1_profile_pic": "389",
    "_key_practice_experts_1_profile_pic": "field_60322b6b0577e",
    "key_practice_experts_1_job_title": "IP Strategist",
    "_key_practice_experts_1_job_title": "field_60322b860577f",
    "key_practice_experts_1_bio": "Zhikang has played an active role in bridging the valley between research and market. He was seconded to the National Research Foundation, where he managed two national-level funding schemes to boost Singapore’s innovation ecosystem. At IPOS, Zhikang was central in developing IP capability, and patent services across ASEAN. In his earlier career, he was part of A*STAR’s team in charge of developing and commercialising Artificial Cell Membranes as a drug discovery platform, which led to a successful spinoff.",
    "_key_practice_experts_1_bio": "field_60322b9605780",
    "key_practice_experts_1_awards_list_0_award": "RMC",
    "_key_practice_experts_1_awards_list_0_award": "field_60322ba905782",
    "key_practice_experts_1_awards_list": "1",
    "_key_practice_experts_1_awards_list": "field_60322b9d05781",
    "key_practice_experts_1_special_mentions_list_0_special_mention": "MIPIM",
    "_key_practice_experts_1_special_mentions_list_0_special_mention": "field_60322bc005784",
    "key_practice_experts_1_special_mentions_list": "1",
    "_key_practice_experts_1_special_mentions_list": "field_60322bb205783",
    "key_practice_experts": "2",
    "_key_practice_experts": "field_60322b0e0577c",
    "special_quotes_0_name": "Mr Tenick Tan",
    "_special_quotes_0_name": "field_60322c31f704e",
    "special_quotes_0_company_name": "ABC Testing Company",
    "_special_quotes_0_company_name": "field_60322c35f704f",
    "special_quotes_0_content": '"I am very pleased with the work that IPOS international team has delivered. I have better understanding of IP now."',
    "_special_quotes_0_content": "field_60322c2af704d",
    "special_quotes": "2",
    "_special_quotes": "field_60322c1bf704c",
    "business_entity": "IPOS International Pte Ltd",
    "_business_entity": "field_60322c82f7051",
    "website": "http://www.iposinternational.com",
    "_website": "field_60322c89f7052",
    "id": "201405679N",
    "_id": "field_60322c91f7053",
    "date_of_formation": "28 February 2014",
    "_date_of_formation": "field_60322c99f7054",
    "last_update": "19 March 2021",
    "_last_update": "field_60322ca4f7055",
    "last_updated_by": "Pei Wen",
    "_last_updated_by": "field_60322cc0f7056",
    "areas": "",
    "_areas": "field_60322dbf84a80",
    "articles_0_article": "391",
    "_articles_0_article": "field_603739e2fff5b",
    "articles": "1",
    "_articles": "field_603739c8fff5a",
    "corporate_videos_0_video_url": "https://www.youtube.com/watch?v=B93NIp8TUMA",
    "_corporate_videos_0_video_url": "field_60373a0ffff5d",
    "corporate_videos": "1",
    "_corporate_videos": "field_60373a04fff5c",
    "special_quotes_1_name": "MS Tina Lee",
    "_special_quotes_1_name": "field_60322c31f704e",
    "special_quotes_1_company_name": "Fu Tien Pte Ltd",
    "_special_quotes_1_company_name": "field_60322c35f704f",
    "special_quotes_1_content": '"Thank you IPOS international for helping us discover our risks and give us good recommendation on how we can make money from our IP. The service level of the team is excellent."',
    "_special_quotes_1_content": "field_60322c2af704d",
    "_thumbnail_id": "388",
}


def get_meta_values(meta, key, field):
    values = set()
    pass


def parse_meta(meta):
    result = {}
    for item in meta:
        if id_regex.match(item):
            continue

        match = field_regex.match(item)
        if match:
            object_name = match.group("object_name")
            index = int(match.group("index"))
            field_name = match.group("field_name")
            if object_name not in result:
                result[object_name] = [None] * (index + 1)
            elif object_name in result and not isinstance(result[object_name], list):
                result[object_name] = []

            if len(result[object_name]) < index + 1:
                diff = index + 1 - len(result[object_name])
                result[object_name] += [None] * diff

            if result[object_name][index] is None:
                result[object_name][index] = {}
            result[object_name][index][field_name] = meta[item][0]
            continue

        if item in result:
            continue

        result[item] = meta[item][0]

    return result


def search_meta(query, meta):
    result = []

    for m in meta:
        if m[0] == "_":
            continue

        field = ""
        match = field_regex.match(m)

        if match:
            field = match.group("field_name")
        else:
            field = m

        confidence = 0
        tokens = query.split(" ")

        for token in tokens:
            c, _ = fuzzy_search(token, m)
            confidence += c

        if len(tokens) > 1:
            confidence /= len(tokens)

        # print(m, tokens, confidence)

        if confidence >= 0.6:
            result.append((field, meta[m], confidence))

    return result


def test_parse_meta():
    result = parse_meta(meta)

    for key in result:
        print(f"{key} => {result[key]}")

    assert True


def test_search_meta():
    result = search_meta("hourly rate", meta)
    print(result)
    assert False


def test_filter_meta():
    pass
