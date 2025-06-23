import streamlit as st
import pandas as pd
import folium
import numpy as np
from streamlit_folium import st_folium
from xml.etree import ElementTree as ET

# ----------------------
# GPX 경로 좌표 추출
def parse_gpx(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns = {"default": "http://www.topografix.com/GPX/1/1"}
    coords = []
    for trkpt in root.findall(".//default:trkpt", ns):
        lat = float(trkpt.attrib["lat"])
        lon = float(trkpt.attrib["lon"])
        coords.append((lat, lon))
    return coords

# 거리 계산 (Haversine, m 단위)
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

# 거리 필터링
@st.cache_data
def filter_nearby(toilets, route_coords, radius):
    nearby = []
    for _, row in toilets.iterrows():
        lat1, lon1 = row['lat'], row['lon']
        for lat2, lon2 in route_coords:
            if haversine_distance(lat1, lon1, lat2, lon2) <= radius:
                nearby.append(row)
                break
    return pd.DataFrame(nearby)

# ----------------------
# 데이터 로딩
gpx_path = "2024jtbc.gpx"
toilet_path = "Seoul_Open_Restrooms.csv"

route_coords = parse_gpx(gpx_path)
route_sampled = route_coords[::60]  # 좌표 수 줄이기

toilets_df = pd.read_csv(toilet_path, encoding="euc-kr")
toilets_df = toilets_df.rename(columns={"x 좌표": "lon", "y 좌표": "lat"})
toilets_df = toilets_df[['도로명주소', 'lat', 'lon', '개방시간', '장애인화장실 현황']].dropna()

# ----------------------
# Streamlit UI
st.set_page_config(layout="wide")
st.title("🚻 JTBC 마라톤 코스 주변 개방 화장실 안내")
st.markdown("📌 마라톤 경로 반경 내의 공중화장실 정보를 보여줍니다.(Created by Jun)")

# 거리 슬라이더
radius = st.slider(
    "🏃‍♂️ 마라톤 코스로부터 반경 거리 (미터)",
    min_value=20,
    max_value=60,
    value=40,
    step=20  # 20 → 40 → 60만 이동
)

# 필터링 (캐싱)
nearby_df = filter_nearby(toilets_df, route_sampled, radius)

# 지도 생성
center = route_coords[len(route_coords)//2]
m = folium.Map(location=center, zoom_start=13)

# 코스 표시
folium.PolyLine(route_coords, color="blue", weight=5, tooltip="마라톤 코스").add_to(m)

# 마커 표시 (최대 50개)
for _, row in nearby_df.head(50).iterrows():
    folium.Marker(
        location=[row['lat'], row['lon']],
        tooltip=row['도로명주소'],
        popup=folium.Popup(f"""
            <b>주소:</b> {row['도로명주소']}<br>
            <b>개방시간:</b> {row['개방시간']}<br>
            <b>장애인 화장실:</b> {row['장애인화장실 현황']}
        """, max_width=300),
        icon=folium.Icon(color="green", icon="info-sign")
    ).add_to(m)

# 지도 출력
st_folium(m, width=1000, height=600)

# 통계 출력
st.markdown(f"🧮 반경 **{radius}m** 이내 화장실 **{len(nearby_df)}개** 중 최대 **50개** 표시 중입니다.")
