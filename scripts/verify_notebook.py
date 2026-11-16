"""Execute the main notebook in isolation and compare its data and exports."""

import ast
import csv
import json
import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "Thu_nghiem_Dijkstra_Yen_BOA_Thanh_My_Tay.ipynb"
RESULTS = "ket_qua_thu_nghiem_Thanh_My_Tay"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def csv_records(records):
    return [{key: "" if value is None else str(value)
             for key, value in row.items()} for row in records]


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def main():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code_cells = [(i, "".join(cell["source"]))
                  for i, cell in enumerate(notebook["cells"], 1)
                  if cell["cell_type"] == "code"]
    for index, source in code_cells:
        ast.parse(source, filename=f"{NOTEBOOK.name}:cell-{index}")

    shell = InteractiveShell.instance()
    previous_cwd = Path.cwd()
    try:
        with TemporaryDirectory(prefix="thanh_my_tay_verify_") as temporary, working_directory(temporary):
            for index, source in code_cells:
                with capture_output():
                    result = shell.run_cell(source, store_history=False)
                error = result.error_before_exec or result.error_in_exec
                if error is not None:
                    raise RuntimeError(f"Notebook cell {index} failed") from error
            namespace = shell.user_ns
            data = namespace["data"]

            for filename, key in (
                ("data_test/edges_clean.csv", "edges"),
                ("data_test/nodes_clean.csv", "nodes"),
                ("cau_hinh/Moc_doan_ket_xe_Thanh_My_Tay.csv", "markers"),
            ):
                require(read_csv(ROOT / filename) == csv_records(data[key]),
                        f"Embedded data differs: {filename}")
            for filename, key in (
                ("toc_do_gia_dinh_chuan.json", "profile"),
                ("tuyen_duong_ket_xe.json", "corridors"),
            ):
                saved = json.loads((ROOT / "cau_hinh" / filename).read_text(encoding="utf-8"))
                require(saved == data[key], f"Embedded config differs: {filename}")

            pairs = namespace["pairs"]
            original_od = namespace["original_od"]
            expected_pairs = [dict(zip(
                ("od_id", "od_id_goc", "hanh_lang", "tuyen_duong", "node_dau", "node_cuoi"),
                (od, original_od[od], namespace["corridors"][corridor], name, start, end),
            )) for od, corridor, name, start, end in pairs]
            require(read_csv(ROOT / "data_test/cap_od.csv") == expected_pairs,
                    "Embedded OD pairs differ from cap_od.csv")
            require(namespace["OD_CAN_CHAY"] is None and len(pairs) == 10,
                    "Sample verification requires all 10 OD pairs")
            require(len(namespace["primary_results"]) == 40,
                    "Expected 10 OD pairs times four methods")

            generated_dir = Path(temporary) / RESULTS
            generated = {p.name for p in generated_dir.iterdir() if p.is_file()}
            expected = {p.name for p in (ROOT / RESULTS).iterdir() if p.is_file()}
            require(generated == expected, "Export file list differs from samples")
            for filename in sorted(expected):
                actual_path = generated_dir / filename
                sample_path = ROOT / RESULTS / filename
                if actual_path.suffix == ".csv":
                    actual, sample = read_csv(actual_path), read_csv(sample_path)
                else:
                    actual = json.loads(actual_path.read_text(encoding="utf-8"))
                    sample = json.loads(sample_path.read_text(encoding="utf-8"))
                require(actual == sample, f"Computed export differs: {filename}")

            print(f"PASS: executed {len(code_cells)} code cells; embedded data, config and 10 OD pairs match.")
            print(f"PASS: {len(expected)} exports match; {len(namespace['primary_results'])} comparison rows, "
                  f"{len(namespace['alternatives'])} detail rows.")
        print("Sample files were not modified; temporary exports were removed.")
    finally:
        os.chdir(previous_cwd)


if __name__ == "__main__":
    main()
