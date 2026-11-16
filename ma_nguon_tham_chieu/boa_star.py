"""Tìm tuyến ít rẽ nhất giờ cao điểm bằng BOA*.

Cài: python -m pip install openpyxl
Đặt script cùng thư mục với Excel, CSV mốc và JSON tốc độ giả định, rồi chạy:
python boa_star.py
Nguồn BOA*: Hernández Ulloa et al., ICAPS 2020, doi:10.1609/icaps.v30i1.6655.
"""
import argparse
import csv
import json
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from math import fsum, inf, isfinite
from pathlib import Path
from time import perf_counter

from openpyxl import load_workbook


MICROSECONDS = 1_000_000
ARTERIAL_TYPES = {"primary", "secondary", "trunk", "primary_link", "secondary_link", "trunk_link"}
WALKWAY_TYPES = {"footway", "pedestrian", "steps", "path"}
DEFAULT_OD_IDS = ("OD31", "OD32", "OD33", "OD34", "OD35")


@dataclass(frozen=True)
class Edge:
    arc_id: str
    u: str
    v: str
    bearing: float
    duration: int
    congested: bool
    length_m: float
    is_alley: bool
    is_main: bool = False
    speed_key: str = ""


@dataclass(frozen=True)
class ODPair:
    source: str
    target: str
    origin_road: str
    destination_road: str

    @property
    def route_name(self):
        return f"{self.origin_road} → {self.destination_road}"


@dataclass
class Label:
    incoming: Edge | None
    duration: int
    turns: int
    parent: "Label | None"


def records(book, sheet_name, required):
    rows = iter(book[sheet_name].values)
    headers = next(rows, ())
    missing = set(required) - set(headers)
    if missing:
        raise ValueError(f"Sheet {sheet_name} thiếu cột: {', '.join(sorted(missing))}")
    for row in rows:
        if any(value is not None for value in row):
            yield dict(zip(headers, row))


def identifier(value):
    if value is None or not str(value).strip():
        raise ValueError("Gặp ID trống trong dữ liệu Excel.")
    return str(value).strip()


def read_excel(path):
    book = load_workbook(path, read_only=True, data_only=True)
    try:
        nodes = {identifier(row["node_id"]) for row in records(book, "Nodes", ("node_id",))}
        edges = list(records(book, "Directed_Edges", (
            "arc_id", "u", "v", "bearing_deg", "is_congested",
            "congestion_segment_ids", "length_m", "is_alley", "highway", "way_id",
        )))
        pairs = {}
        for row in records(book, "OD_Pairs", ("od_id", "source", "target")):
            od_id, source, target = (identifier(row[k]) for k in ("od_id", "source", "target"))
            if od_id in pairs or source not in nodes or target not in nodes:
                raise ValueError(f"OD không hợp lệ: {od_id} ({source} → {target})")
            pairs[od_id] = ODPair(source, target, row.get("origin_road") or source,
                                 row.get("destination_road") or target)
        seen = set()
        for row in edges:
            arc_id, u, v = (identifier(row[k]) for k in ("arc_id", "u", "v"))
            if arc_id in seen or u not in nodes or v not in nodes:
                raise ValueError(f"Cạnh không hợp lệ: {arc_id} ({u} → {v})")
            seen.add(arc_id)
        return edges, pairs
    finally:
        book.close()


def edge_flag(row, field, arc_id):
    value = str(row[field]).strip().lower()
    if value not in {"true", "false", "1", "0"}:
        raise ValueError(f"Cờ {field} không hợp lệ ở cạnh {arc_id}.")
    return value in {"true", "1"}


def read_speed_profile(path):
    with path.open(encoding="utf-8-sig") as file:
        profile = json.load(file)
    for section, fields in (
        ("toc_do_kmh", ("duong_chinh", "duong_noi_bo_khong_phai_hem",
                        "hem_cap_1", "hem_cap_2", "hem_cap_3_va_khong_ten", "duong_di_bo")),
        ("toc_do_ket_xe_kmh_theo_ma_doan", tuple(profile["toc_do_ket_xe_kmh_theo_ma_doan"])),
        ("nguong_be_rong_hem_m", ("hem_cap_1", "hem_cap_2")),
        ("be_rong_hem_m_theo_osm_way_id", tuple(profile["be_rong_hem_m_theo_osm_way_id"])),
        ("do_tre_re_giay", ("di_thang", "re_phai", "re_trai", "quay_dau",
                            "re_trai_tu_hem_ra_truc_chinh_phat_them", "phat_hem_cut")),
    ):
        for field in fields:
            if field not in profile[section]:
                raise ValueError(f"Thiếu thông số trong JSON: {section}.{field}")
            raw_value = profile[section][field]
            if isinstance(raw_value, bool):
                raise ValueError(f"Thông số phải là số: {section}.{field}")
            value = float(raw_value)
            if not isfinite(value) or value < 0 or (section != "do_tre_re_giay" and value == 0):
                raise ValueError(f"Thông số không hợp lệ: {section}.{field}")
            profile[section][field] = value
    thresholds = profile["nguong_be_rong_hem_m"]
    if thresholds["hem_cap_1"] <= thresholds["hem_cap_2"]:
        raise ValueError("Ngưỡng bề rộng hẻm cấp 1 phải lớn hơn ngưỡng cấp 2.")
    return profile


def read_congestion_markers(markers, profile):
    with markers.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    missing = {identifier(row["stt"]) for row in rows}
    missing -= profile["toc_do_ket_xe_kmh_theo_ma_doan"].keys()
    if missing:
        raise ValueError("Thiếu tốc độ trong JSON cho mã đoạn kẹt: " + ", ".join(sorted(missing)))
    return {identifier(row["stt"]) for row in rows
            if row["node_dau_osm"].strip() and row["node_cuoi_osm"].strip()}


def build_peak_graph(rows, profile, marked_segments):
    speeds = profile["toc_do_kmh"]
    congestion_speeds = profile["toc_do_ket_xe_kmh_theo_ma_doan"]
    thresholds = profile["nguong_be_rong_hem_m"]
    widths = profile["be_rong_hem_m_theo_osm_way_id"]
    outgoing, incoming = defaultdict(list), defaultdict(list)
    for row in rows:
        arc_id = identifier(row["arc_id"])
        u, v = identifier(row["u"]), identifier(row["v"])
        is_alley = edge_flag(row, "is_alley", arc_id)
        length_m = float(row["length_m"])
        bearing = float(row["bearing_deg"]) if row["bearing_deg"] is not None else 0.0
        if not isfinite(bearing) or not isfinite(length_m) or length_m < 0:
            raise ValueError(f"Chiều dài hoặc góc hướng không hợp lệ ở cạnh {arc_id}.")
        congested = edge_flag(row, "is_congested", arc_id)
        highway = row.get("highway")
        is_main = not is_alley and (
            highway in ARTERIAL_TYPES or bool(row.get("axis"))
            or row.get("name") in {"Đường D5", "D5"}
            or congested
        )
        if congested:
            code = identifier(row["congestion_segment_ids"])
            if code not in marked_segments:
                raise ValueError(f"Cạnh {arc_id} có đoạn kẹt {code} thiếu mốc đầu hoặc cuối.")
            if code not in congestion_speeds:
                raise ValueError(f"Thiếu tốc độ giả định cho đoạn kẹt {code} trong JSON (cạnh {arc_id}).")
            speed_key = f"ket_xe:{code}"
            speed = congestion_speeds[code]
        else:
            if highway in WALKWAY_TYPES:
                speed_key = "duong_di_bo"
            elif is_alley:
                width = widths.get(identifier(row["way_id"]), 0)
                if width >= thresholds["hem_cap_1"]:
                    speed_key = "hem_cap_1"
                elif width >= thresholds["hem_cap_2"]:
                    speed_key = "hem_cap_2"
                else:
                    speed_key = "hem_cap_3_va_khong_ten"
            elif is_main:
                speed_key = "duong_chinh"
            else:
                speed_key = "duong_noi_bo_khong_phai_hem"
            speed = speeds[speed_key]
        seconds = length_m * 3.6 / speed

        edge = Edge(arc_id, u, v, bearing, round(seconds * MICROSECONDS),
                    congested, length_m, is_alley, is_main, speed_key)
        outgoing[u].append(edge)
        incoming[v].append(edge)
    return outgoing, incoming


def turn_cost(previous, following, threshold):
    if previous is None:
        return 0
    angle = abs((following.bearing - previous.bearing + 180) % 360 - 180)
    return int(angle > threshold)


def network_nodes(outgoing):
    """Nhận diện nút giao và nhánh hẻm cụt trên đồ thị bỏ hướng."""
    neighbors = defaultdict(set)
    protected = set()
    for edges in outgoing.values():
        for edge in edges:
            if not edge.is_alley:
                protected.update((edge.u, edge.v))
            if edge.u != edge.v:
                neighbors[edge.u].add(edge.v)
                neighbors[edge.v].add(edge.u)

    junctions = {node for node, adjacent in neighbors.items() if len(adjacent) >= 3}
    leaves = deque(node for node, adjacent in neighbors.items()
                   if len(adjacent) == 1 and node not in protected)
    removed = []
    while leaves:
        node = leaves.popleft()
        if len(neighbors[node]) != 1:
            continue
        parent = neighbors[node].pop()
        neighbors[parent].remove(node)
        removed.append((node, parent))
        if len(neighbors[parent]) == 1 and parent not in protected:
            leaves.append(parent)

    branches = {}
    for node, parent in reversed(removed):
        branches[node] = branches.get(parent, node)
    return junctions, branches


def enters_dead_end(edge, target, branches):
    branch = branches.get(edge.v)
    return (branch is not None and branches.get(edge.u) != branch
            and branches.get(target) != branch)


def turn_delay(previous, following, threshold, delays, junctions):
    if delays is None or previous is None:
        return 0
    delta = (following.bearing - previous.bearing + 180) % 360 - 180
    if previous.u == following.v:
        seconds = delays["quay_dau"]
    elif previous.v not in junctions:
        return 0
    elif abs(delta) >= 150:
        seconds = delays["quay_dau"]
    elif abs(delta) <= threshold:
        seconds = delays["di_thang"]
    elif delta > 0:
        seconds = delays["re_phai"]
    else:
        seconds = delays["re_trai"]
        if previous.is_alley and following.is_main and following.congested:
            seconds += delays["re_trai_tu_hem_ra_truc_chinh_phat_them"]
    return round(seconds * MICROSECONDS)


def remaining_times(incoming, target):
    """Dijkstra ngược trên node: cận dưới nhất quán cho thời gian còn lại."""
    distances = {target: 0}
    queue = [(0, target)]
    while queue:
        cost, node = heappop(queue)
        if cost != distances[node]:
            continue
        for edge in incoming.get(node, ()):
            candidate = cost + edge.duration
            if candidate < distances.get(edge.u, inf):
                distances[edge.u] = candidate
                heappush(queue, (candidate, edge.u))
    return distances


def remaining_turns(incoming, target, threshold):
    """Tìm số lần rẽ ít nhất còn lại, theo cạnh vừa đi vào."""
    distances = {}
    queue = []
    for edge in incoming.get(target, ()):
        distances[edge.arc_id] = 0
        heappush(queue, (0, edge.arc_id, edge))
    while queue:
        cost, arc_id, edge = heappop(queue)
        if cost != distances[arc_id]:
            continue
        for previous in incoming.get(edge.u, ()):
            candidate = cost + turn_cost(previous, edge, threshold)
            if candidate < distances.get(previous.arc_id, inf):
                distances[previous.arc_id] = candidate
                heappush(queue, (candidate, previous.arc_id, previous))
    return distances


def boa_star(outgoing, incoming, source, target, threshold, delays, junctions, branches):
    """Trả một lộ trình cho mỗi cặp chi phí (thời gian, số lần rẽ) Pareto."""
    start = Label(None, 0, 0, None)
    if source == target:
        return [start]
    dead_end_penalty = round(delays["phat_hem_cut"] * MICROSECONDS)
    h_time = remaining_times(incoming, target)
    if source not in h_time:
        return []
    h_turn = remaining_turns(incoming, target, threshold)
    sequence = count()
    queue = [(h_time[source], 0, next(sequence), start)]
    fewest_turns_at_state = {}
    fewest_turns_at_goal = inf
    solutions = []

    while queue:
        _, estimated_turns, _, label = heappop(queue)
        edge = label.incoming
        state = edge.arc_id if edge else None
        if (label.turns >= fewest_turns_at_state.get(state, inf)
                or estimated_turns >= fewest_turns_at_goal):
            continue

        # Cùng state có cùng heuristic. Thứ tự heap bảo đảm thời gian
        # tích lũy không giảm ở state đó, nên chỉ cần lưu số lần rẽ nhỏ nhất.
        fewest_turns_at_state[state] = label.turns
        node = edge.v if edge else source
        if node == target:
            solutions.append(label)
            fewest_turns_at_goal = label.turns
            continue

        for following in outgoing.get(node, ()):
            if following.arc_id not in h_turn:
                continue
            turns = label.turns + turn_cost(edge, following, threshold)
            lower_bound = turns + h_turn[following.arc_id]
            if (turns >= fewest_turns_at_state.get(following.arc_id, inf)
                    or lower_bound >= fewest_turns_at_goal):
                continue
            duration = (label.duration + following.duration
                        + turn_delay(edge, following, threshold, delays, junctions))
            if enters_dead_end(following, target, branches):
                duration += dead_end_penalty
            child = Label(following, duration, turns, label)
            heappush(queue, (duration + h_time[following.v], lower_bound,
                            next(sequence), child))
    return solutions


def route_edges(label):
    edges = []
    while label.incoming is not None:
        edges.append(label.incoming)
        label = label.parent
    return edges[::-1]


def route_metrics(route):
    length_m = fsum(edge.length_m for edge in route)
    alley_m = fsum(edge.length_m for edge in route if edge.is_alley)
    return length_m, 100 * alley_m / length_m if length_m else 0.0


def print_report(od_ids, pairs, selected):
    headers = ("STT", "Mã OD", "Tuyến đường", "Quãng đường (km)", "Thời gian (phút)",
               "Số lần rẽ", "Tỷ lệ đi hẻm (%)", "Cạnh kẹt", "Trễ tại nút (s)")
    rows = [headers]
    for index, od in enumerate(od_ids, 1):
        result = selected.get(od)
        if result is None:
            values = ("—", "Không có đường", "—", "—", "—", "—")
        else:
            solution, length_m, alley_pct, congested_count, delay_s = result
            values = (f"{length_m / 1000:.2f}", f"{solution.duration / MICROSECONDS / 60:.2f}",
                      str(solution.turns), f"{alley_pct:.1f}", str(congested_count), f"{delay_s:g}")
        rows.append((str(index), od, pairs[od].route_name, *values))

    widths = [max(map(len, column)) for column in zip(*rows)]
    print(f"\nBOA* – Tuyến ít rẽ nhất giờ cao điểm ({len(selected)}/{len(od_ids)} cặp có đường đi)")
    for row in rows:
        print(" | ".join(value.ljust(width) for value, width in zip(row, widths)).rstrip())


def main():
    parser = argparse.ArgumentParser(description="BOA*: thời gian di chuyển và số lần rẽ.")
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent,
                        help="Thư mục chứa Du_lieu_test.xlsx và các tệp cấu hình.")
    parser.add_argument("--input", type=Path,
                        help="Chọn Excel khác.")
    parser.add_argument("--od", nargs="+", metavar="OD_ID",
                        help="Mặc định chạy OD31–OD35. Dùng --od all để chạy toàn bộ.")
    parser.add_argument("--turn-angle", type=float, default=35,
                        help="Đếm rẽ khi góc đổi hướng lớn hơn ngưỡng này, mặc định 35°.")
    parser.add_argument("--speed-profile", type=Path, help="JSON tốc độ và độ trễ nút giao.")
    parser.add_argument("--markers", type=Path, help="CSV mốc đầu và cuối đoạn kẹt.")
    parser.add_argument("--output", type=Path, help="Nơi lưu CSV kết quả Pareto.")
    args = parser.parse_args()
    if not 0 < args.turn_angle <= 180:
        parser.error("--turn-angle phải lớn hơn 0 và không quá 180.")
    input_path = args.input or args.data_dir / "Du_lieu_test.xlsx"
    directory = input_path.parent
    markers_path = args.markers or directory / "Moc_doan_ket_xe_Thanh_My_Tay.csv"
    profile_path = args.speed_profile or directory / "toc_do_gia_dinh_chuan.json"
    output_path = args.output or directory / "boa_star_results.csv"
    if (output_path.suffix.lower() != ".csv"
            or output_path.resolve() in {input_path.resolve(), markers_path.resolve(),
                                         profile_path.resolve()}):
        parser.error("--output phải là đường dẫn CSV riêng.")
    try:
        rows, pairs = read_excel(input_path)
        requested = list(dict.fromkeys(od.upper() for od in (args.od or DEFAULT_OD_IDS)))
        od_ids = list(pairs) if requested == ["ALL"] else requested
        unknown = [od for od in od_ids if od not in pairs]
        if unknown:
            parser.error("Không có mã OD: " + ", ".join(unknown))
        profile = read_speed_profile(profile_path)
        marked_segments = read_congestion_markers(markers_path, profile)
        graph = build_peak_graph(rows, profile, marked_segments)
        delays = profile["do_tre_re_giay"]
        junctions, branches = network_nodes(graph[0])
    except (OSError, KeyError, ValueError, TypeError) as exc:
        parser.error(str(exc))

    headers = ["od_id", "scenario", "source", "target", "status", "pareto_rank",
               "travel_time_s", "turn_count", "congested_edge_count", "node_ids",
               "arc_ids", "runtime_ms", "turn_angle_deg", "route_name", "distance_m",
               "alley_pct", "edge_time_s", "junction_delay_s", "selected_fewest_turns",
               "dead_end_penalty_s"]
    fewest_turns = {}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        for od in od_ids:
            pair = pairs[od]
            source, target = pair.source, pair.target
            started = perf_counter()
            solutions = boa_star(*graph, source, target, args.turn_angle, delays, junctions, branches)
            elapsed = round((perf_counter() - started) * 1000, 3)
            prefix = [od, "peak", source, target]
            if not solutions:
                writer.writerow([*prefix, "no_path", *([None] * 6), elapsed,
                                 args.turn_angle, pair.route_name, *([None] * 4), False, None])
                continue
            selected = min(solutions, key=lambda route: (route.turns, route.duration))
            for rank, solution in enumerate(solutions, 1):
                route = route_edges(solution)
                length_m, alley_pct = route_metrics(route)
                edge_time = sum(edge.duration for edge in route)
                penalty = sum(enters_dead_end(edge, target, branches) for edge in route)
                penalty *= round(delays["phat_hem_cut"] * MICROSECONDS)
                delay_s = (solution.duration - edge_time - penalty) / MICROSECONDS
                congested_count = sum(edge.congested for edge in route)
                is_selected = solution is selected
                if is_selected:
                    fewest_turns[od] = (solution, length_m, alley_pct, congested_count, delay_s)
                writer.writerow([
                    *prefix, "ok", rank, solution.duration / MICROSECONDS, solution.turns,
                    congested_count,
                    json.dumps([source, *(edge.v for edge in route)]),
                    json.dumps([edge.arc_id for edge in route]), elapsed, args.turn_angle,
                    pair.route_name, round(length_m, 6), round(alley_pct, 6),
                    edge_time / MICROSECONDS, delay_s, is_selected, penalty / MICROSECONDS,
                ])
    print(f"Một lần rẽ được tính khi góc đổi hướng lớn hơn {args.turn_angle:g}°.")
    print_report(od_ids, pairs, fewest_turns)
    counts = Counter(edge.speed_key for edges in graph[0].values() for edge in edges)
    print("\nSố cung theo thông số tốc độ trong JSON:")
    for key in profile["toc_do_kmh"]:
        print(f"  {key}: {counts[key]}")
    for code in profile["toc_do_ket_xe_kmh_theo_ma_doan"]:
        print(f"  ket_xe:{code}: {counts[f'ket_xe:{code}']}")
    print(f"\nCSV chi tiết các phương án Pareto: {output_path}")


if __name__ == "__main__":
    main()
