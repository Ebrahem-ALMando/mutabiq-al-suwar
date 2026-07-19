"""نموذج نتائج افتراضي ومرشح دون إنشاء widget لكل صف."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt

from models.result_models import ResultRecord
from utils.constants import COPY_STATUS_AR, MATCH_STATUS_AR


class ResultTableModel(QAbstractTableModel):
    HEADERS = [
        "صف Excel",
        "المعرّف",
        "الاسم",
        "حالة المطابقة",
        "النسبة",
        "عدد الصور",
        "الصورة المحددة",
        "اسم الوجهة",
        "حالة النسخ",
        "ملاحظات",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.records: list[ResultRecord] = []

    def set_records(self, records: list[ResultRecord]) -> None:
        self.beginResetModel()
        self.records = records
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self.records)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return super().headerData(section, orientation, role)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self.records):
            return None
        record = self.records[index.row()]
        if role == Qt.ItemDataRole.UserRole:
            return record.match_status.value
        if role == Qt.ItemDataRole.UserRole + 1:
            return record
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        if role == Qt.ItemDataRole.DisplayRole:
            return [
                record.excel_row,
                record.identifier,
                record.secondary_name,
                MATCH_STATUS_AR[record.match_status.value],
                f"{record.similarity_score:.0%}" if record.similarity_score is not None else "—",
                len(record.candidate_paths) or int(bool(record.source_path)),
                record.source_filename,
                record.destination_filename_override or record.destination_filename,
                COPY_STATUS_AR[record.copy_status.value],
                record.notes,
            ][index.column()]
        return None

    def record(self, row: int) -> ResultRecord | None:
        return self.records[row] if 0 <= row < len(self.records) else None

    def notify_record_changed(self, row: int) -> None:
        self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))


class ResultFilterProxy(QSortFilterProxyModel):
    def __init__(self) -> None:
        super().__init__()
        self.search_text = ""
        self.status = ""
        self.setDynamicSortFilter(True)

    def set_search(self, text: str) -> None:
        self.beginFilterChange()
        self.search_text = text.casefold().strip()
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def set_status(self, status: str) -> None:
        self.beginFilterChange()
        self.status = status
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        status = model.index(source_row, 0).data(Qt.ItemDataRole.UserRole)
        if self.status and status != self.status:
            return False
        if not self.search_text:
            return True
        return any(
            self.search_text in str(model.index(source_row, column).data() or "").casefold()
            for column in range(model.columnCount())
        )
