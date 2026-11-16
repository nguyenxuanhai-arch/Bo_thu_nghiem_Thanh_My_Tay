import json
import pandas as pd
import networkx as nx

# Đường dẫn file dữ liệu Excel
FILE_EXCEL = 'Du_lieu_test.xlsx'

# Đọc danh sách các cặp OD từ sheet OD_Pairs
df_od = pd.read_excel(FILE_EXCEL, sheet_name='OD_Pairs')

# Lấy 5 cặp tuyến đường trọng điểm (OD31 đến OD35 trong file test)
df_od_5 = df_od.tail(5).copy()
print("5 cặp tuyến đường cần tìm:")
for _, r in df_od_5.iterrows():
    print(f"  • [{r['od_id']}] {r['origin_road']} -> {r['destination_road']} (Node {r['source']} -> {r['target']}) | Khoảng cách chim bay: {r['straight_line_distance_m']/1000:.2f} km")

df_nodes = pd.read_excel(FILE_EXCEL, sheet_name='Nodes')
df_edges = pd.read_excel(FILE_EXCEL, sheet_name='Directed_Edges')

# Tạo từ điển tọa độ theo node_id
toa_do = {int(r['node_id']): (float(r['lat']), float(r['lon'])) for _, r in df_nodes.iterrows()}

print(f"Đã nạp {len(toa_do)} nodes và {len(df_edges)} cung đường có hướng từ file Excel.")

with open('tuyen_duong_ket_xe.json', 'r', encoding='utf-8') as f:
    DS_KET_XE = json.load(f)['danh_sach_tuyen_ket_xe']
df_moc = pd.read_csv('Moc_doan_ket_xe_Thanh_My_Tay.csv')

BIEN = 0.0003  # ~30m
def doc_toa_do(chuoi):
    return [tuple(map(float, p.split(','))) for p in str(chuoi).split('|')]

for tuyen in DS_KET_XE:
    pv = dict(tuyen['pham_vi_toa_do'])
    moc = df_moc[df_moc['stt'] == tuyen['stt']]
    if len(moc) and str(moc.iloc[0]['trang_thai']).startswith('Đủ hai mốc'):
        pts = doc_toa_do(moc.iloc[0]['toa_do_dau_lat_lon']) + doc_toa_do(moc.iloc[0]['toa_do_cuoi_lat_lon'])
        pv = {'lat_min': min(p[0] for p in pts) - BIEN, 'lat_max': max(p[0] for p in pts) + BIEN,
              'lon_min': min(p[1] for p in pts) - BIEN, 'lon_max': max(p[1] for p in pts) + BIEN}
    tuyen['pv_ap_dung'] = pv

def toc_do_ket_xe(ten, la_hem, u, v):
    """Trả về tốc độ kẹt xe (km/h) nếu cạnh nằm trong đoạn kẹt, ngược lại None."""
    if la_hem:
        return None
    lat = (toa_do[u][0] + toa_do[v][0]) / 2
    lon = (toa_do[u][1] + toa_do[v][1]) / 2
    v_min = None
    for tuyen in DS_KET_XE:
        pv = tuyen['pv_ap_dung']
        if any(k in ten for k in tuyen['tu_khoa_nhan_dien']) and \
           pv['lat_min'] <= lat <= pv['lat_max'] and pv['lon_min'] <= lon <= pv['lon_max']:
            v_min = tuyen['toc_do_gio_cao_diem_kmh'] if v_min is None else min(v_min, tuyen['toc_do_gio_cao_diem_kmh'])
    return v_min

G = nx.DiGraph()
so_canh_ket = 0

for _, r in df_edges.iterrows():
    u, v = int(r['u']), int(r['v'])
    if u not in toa_do or v not in toa_do:
        continue
    do_dai = float(r['length_m'])
    thoi_gian = float(r['peak_time_s']) if pd.notna(r['peak_time_s']) else float(r['time_s'])
    la_hem = bool(r['is_alley'])
    ten = str(r['name']) if pd.notna(r['name']) else 'Hẻm không tên'
    goc = float(r['bearing_deg']) if pd.notna(r['bearing_deg']) else 0.0

    v_kx = toc_do_ket_xe(ten, la_hem, u, v)
    if v_kx is not None:
        thoi_gian = max(thoi_gian, do_dai / (v_kx / 3.6))
        so_canh_ket += 1

    if G.has_edge(u, v) and G[u][v]['weight'] <= thoi_gian:
        continue
    G.add_edge(u, v, weight=thoi_gian, do_dai=do_dai, la_hem=la_hem, ten=ten, goc=goc)

print(f"Đồ thị: {G.number_of_nodes()} nút, {G.number_of_edges()} cạnh. Áp dụng kẹt xe cho {so_canh_ket} cạnh.")

def dem_so_lan_re(cac_canh):
    so_lan = 0
    for a, b in zip(cac_canh, cac_canh[1:]):
        delta = (b['goc'] - a['goc'] + 180) % 360 - 180
        if abs(delta) > 35.0:
            so_lan += 1
    return so_lan

bang_ket_qua = []
for _, r in df_od_5.iterrows():
    s, t = int(r['source']), int(r['target'])
    ten = f"{r['origin_road']} -> {r['destination_road']}"
    try:
        path = nx.dijkstra_path(G, s, t, weight='weight')
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        print(f"Không tìm thấy đường cho {r['od_id']}: {ten}")
        continue

    cac_canh = [G[a][b] for a, b in zip(path, path[1:])]
    tong_m = sum(c['do_dai'] for c in cac_canh)
    hem_m = sum(c['do_dai'] for c in cac_canh if c['la_hem'])
    tong_s = sum(c['weight'] for c in cac_canh)

    bang_ket_qua.append({
        "Mã OD": r['od_id'],
        "Tuyến đường": ten,
        "Tổng quãng đường đi (km)": round(tong_m / 1000, 2),
        "Thời gian di chuyển (phút)": round(tong_s / 60, 2),
        "Tổng số lần rẽ": dem_so_lan_re(cac_canh),
        "Tỷ lệ đi hẻm (%)": round(hem_m / tong_m * 100, 1) if tong_m > 0 else 0.0
    })

print("Kết quả 5 cặp tuyến đường (Dijkstra):")
for d in bang_ket_qua:
    print(f"  • [{d['Mã OD']}] {d['Tuyến đường']}: {d['Tổng quãng đường đi (km)']:.2f} km | "
          f"{d['Thời gian di chuyển (phút)']:.2f} phút | {d['Tổng số lần rẽ']} lần rẽ | "
          f"{d['Tỷ lệ đi hẻm (%)']:.1f}% hẻm")

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 250)
pd.set_option('display.unicode.east_asian_width', True)
df_ket_qua = pd.DataFrame(bang_ket_qua)
print()
print(df_ket_qua)
