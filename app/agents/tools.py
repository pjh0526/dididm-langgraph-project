from __future__ import annotations

from typing import Any

import httpx
from elasticsearch import Elasticsearch
from langchain.tools import tool
from langchain_elasticsearch import ElasticsearchRetriever

_ES_URL = "https://elasticsearch-edu.didim365.app"
_ES_USER = "elastic"
_ES_PASSWORD = "FJl79PA7mMIJajxB1OHgdLEe"
_INDEX_NAME = "edu-collection"
_CONTENT_FIELD = "content"
_TOP_K = 5

_DRUG_API_URL = "https://apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList"
_DRUG_API_KEY = "72c6779aea30770c960a2620ae1c96d6acb8ab33c5c1fdb404b91ac8864927e0e"

_HOSP_API_URL = "https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList"
_HOSP_API_KEY = "72c6779aea30770c960a2620ae1c96d6acb8ab33c5c1fdb404b91ac8864927e0e"

_SIDO_CODE: dict[str, str] = {
  "서울": "110000", "서울특별시": "110000",
  "부산": "210000", "부산광역시": "210000",  
  "대구": "220000", "대구광역시": "220000",
  "인천": "230000", "인천광역시": "230000",
  "광주": "240000", "광주광역시": "240000",
  "대전": "250000", "대전광역시": "250000",
  "울산": "260000", "울산광역시": "260000",
  "세종": "290000", "세종특별자치시": "290000",
  "경기": "410000", "경기도": "410000",
  "강원": "420000", "강원도": "420000", "강원특별자치도": "420000",
  "충북": "430000", "충청북도": "430000",
  "충남": "440000", "충청남도": "440000",
  "전북": "450000", "전라북도": "450000", "전라특별자치도": "450000",
  "전남": "460000", "전라남도": "460000",
  "경북": "470000", "경상북도": "470000",
  "경남": "480000", "경상남도": "480000",
  "제주": "490000", "제주특별자치도": "490000",
}
_DEPT_CODE: dict[str, str] = {
  "정신건강의학과": "03", "정신과": "03",
  "외과": "04",
  "정형외과": "05",
  "신경외과": "06",
  "심장혈관흉부외과": "07", "흉부외과": "07",
  "성형외과": "08",
  "마취통증의학과": "09", "마취과": "09",
  "산부인과": "10", "산부과": "10",
  "소아청소년과": "11", "소아과": "11",
  "안과": "12",
  "이비인후과": "13",
  "피부과": "14",
  "비뇨의학과": "15", "비뇨과": "15",
  "영상의학과": "16",
  "방사선의학과": "17",
  "병리과": "18",
  "진단검사의학과": "19",
  "결핵과": "20",
  "재활의학과": "21", "재활과": "21",
  "핵의학과": "22",
  "가정의학과": "23",
  "응급의학과": "24", "응급과": "24",
  "작업환경의학과": "25",
  "예방의학과": "26",
  "한방": "28",
  "한방내과": "80",
  "한방부인과": "81",
  "한방소아과": "82",
  "침구과": "85",
  "한방재활의학과": "86",
  "사상패질과": "87",
}

def _bm25_query(search_query:str) -> dict[str, Any]:
  """BM25 match 쿼리 빌더 함수 [ElasticsearchRetriever body_func 구조]"""
  return {
    "query": {
      "match": {
        _CONTENT_FIELD: {
          "query": search_query,
          "operator": "or",
        }
      }
    },
    "size": _TOP_K,
  }

def _build_retriever() -> ElasticsearchRetriever:
  es_client = Elasticsearch(
    _ES_URL,
    basic_auth=(_ES_USER, _ES_PASSWORD),
    verify_certs=False,
  )
  return ElasticsearchRetriever(
    index_name=_INDEX_NAME,
    body_func=_bm25_query,
    content_field=_CONTENT_FIELD,
    client=es_client
  )


_retriever: ElasticsearchRetriever | None = None

def _get_retriever() -> ElasticsearchRetriever:
  global _retriever
  if _retriever is None:
      _retriever = _build_retriever()
  return _retriever


@tool
def search_symptoms(symtoms: str) -> str:
  """주어진 증상(쉼표로 구분)을 기반으로 Elasticsearch에서 관련 의료 정보를 검색합니다. """
  retriever = _get_retriever()
  docs = retriever.invoke(symtoms)
  if not docs:
      return f"증상 `{symtoms}`에 대한 관련 의료 정보를 찾을 수 없습니다."
  
  results: list[str] = []
  for i, doc in enumerate(docs, 1):
    source_spec = doc.metadata.get("_source", {}).get("source_spec", "unknown")
    creation_year = doc.metadata.get("_source", {}).get("creation_year", "")
    header = f"[{i}] 출처: {source_spec}" + (f" ({creation_year}년)" if creation_year and creation_year != "null" else "")
    snippet = doc.page_content[:500].replace("\n", " ")
    results.append(f"{header}\n{snippet}")

  return "\n\n".join(results)
  
@tool
def get_medication_info(medication_name: str) -> str:
  """약물 이름을 받아 식품약품안전진술인러비스(e약은요) API에서 효능, 사용법, 주의사항, 부작용, 보관법 등을 조회합니다. """
  try: 
    resp = httpx.get(
      _DRUG_API_URL,
      params={
        "serviceKey": _DRUG_API_KEY,
        "itemName": medication_name,
        "type": "json",
        "numOfRows": 3,
        "pageNo": 1
      },
      timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

  except httpx.HTTPStatusError as e:
    return f"약물 정보 API 호출 실패 (HTTP {e.response.status_code}): {e.response.text[:200]}"
  except httpx.RequestError as e:
    return f"약물 정보 API 네트워크 오류: {e}"
  except Exception as e:
    return f"약물 정보 조회 중 오류 발생: {e}"

  items: list[Any] = (
    data.get("body", {}).get("items", [])
    or data.get("response", {}).get("body", {}).get("items", [])
    or []
  )
  
  if isinstance(items, dict):
    items = [items]

  if not items:
    return f"'{medication_name}'에 대한 의약품 정보를 찾을 수 없습니다. "

  lines: list[str] = []
  for item in items:
    name = item.get("itemName", medication_name)
    entp = item.get("entpName", "")
    lines.append(f" 제품명: {name}" + (f"({entp})(" if entp else ""))

    field_map = {
      "efcyQesitm": "효능",
      "useMethodQesitm": "사용법",
      "atpnWarnQesitm": "주의사항(경고)",
      "atpnQesitm": "주의사항",
      "intrcQesitm": "상호작용",
      "seQesitm": "부작용",
      "depositMethodQesitm": "보관법",
    }
    for field, label in field_map.items():
      value = item.get(field)
      if value:
        lines.append(f" [{label}] {value}")
    lines.append("")

  return "\n".join(lines).strip()

@tool
def find_nearby_hospitals(location: str, specialty: str = "일반") -> str:
    """
    지역명과 병원 종별(speciality)을 기반으로 건강보험심사위원가원 병원정보서비스에서 병워 목록을 조회합니다.
    location: 시도명 (예: '서울', '부산', '경기') 또는 병원명 일부
    specialty: 병원 종별 (예: '의원', '종합병원', '한의원', '치과', '일반')
    """
    import xml.etree.cElementTree as ET

    sido_cd = None
    yadm_nm = None
    for key, code in _SIDO_CODE.items():
      if key in location :
        sido_cd = code
        break
    if sido_cd is None:
      yadm_nm = location

    cl_cd = _CL_CODE.get(specialty)
    dept_cd = _DEPT_CODE.get(specialty)

    params: dict[str, Any] = {
      "serviceKey": _HOSP_API_KEY,
      "pageNo": "1",
      "numOfRows": "5",
    }
    if sido_cd:
      params["sidoCd"] = sido_cd
    if yadm_nm:
      params["yadmNm"] = yadm_nm
    if dept_cd:
      params["dgsbjtCd"] = dept_cd
    elif cl_cd:
      params["clCd"] = cl_cd

    try:
      resp = httpx.get(_HOSP_API_URL, params=params, timeout=15)
      resp.raise_for_status()
    except httpx.HTTPStatusError as e:
      return f"병원 정보 API 호출 실패 (HTTP {e.response.status_code}: {e.response.text[:200]})"
    except httpx.RequestError as e:
      return f"병원 정보 APi 네트워크 오류 : {e}"

    try:
      root = ET.fromstring(resp.content)
    except ET.ParseError as e:
      return f"병원 정보 응답 파싱 오류: {e}"

    result_code = root.findtext(".//resultCode", "")
    if result_code != "00":
        result_msg = root.findtext(".//resultMsg", "")
        return f"병원 정보 API 오류 ({result_code}): {result_msg}"

    items = root.findall(".//item")
    total = root.findtext(".//totalCount", 0)
    
    if not items:
      return f"'{location}' 지역의 {speciality} 병원 정보를 찾을 수 없습니다."
    lines: list[str] = [
      f"'{location} {specialty} 병원 목록 (전체 {total}건 중 상위 {len(items)}건)",
      ""
    ]
    for i, item in enumerate(items, i):
      name = item.findtext("yadmNm", "")
      cl_name = item.findtext("clCdNm", "")
      addr = item.findtext("addr", "")
      tel = item.findtext("telno", "")
      dr_cnt = item.findtext("drTotCnt", "")
      url = item.findtext("hospUrl", "")
      lines.append(f"{i}. {name} ({cl_name})")
      lines.append(f"  주소: {addr}")
      if tel:
        lines.append(f"  전화: {tel}")
      if dr_cnt and dr_cnt !="0":
        lines.append(f" 이자 수: {dr_cnt}명")
      if url:
        lines.append(f" 홈페이지: {url}")
      lines.append("")

    return "\n".join(lines).strip()