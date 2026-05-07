from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass(frozen=True)
class ChunkPiece:
    text: str
    chunk_index: int
    chunk_count: int


class RecursiveTextSplitter:
    """Split long paragraph-level text into smaller retrieval chunks.

    The splitter prefers paragraph boundaries first, then sentence boundaries,
    then whitespace, and finally hard character cuts when needed.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 120) -> None:
        self.chunk_size = max(1, chunk_size)
        self.chunk_overlap = max(0, min(chunk_overlap, self.chunk_size - 1))

    def split_text(self, text: str, content_type: str | None = None) -> List[str]:
        normalized = text.strip()
        if not normalized:
            return []

        if self._looks_like_table(normalized, content_type):
            table_chunks = self._split_table(normalized)
            if table_chunks:
                return table_chunks

        chunks: List[str] = []
        for paragraph in self._split_by_paragraphs(normalized):
            if len(paragraph) <= self.chunk_size:
                chunks.append(paragraph)
                continue
            chunks.extend(self._split_recursive(paragraph))
        return self._merge_small_chunks(chunks)

    def split_piece(self, text: str, content_type: str | None = None) -> List[ChunkPiece]:
        chunks = self.split_text(text, content_type=content_type)
        total = len(chunks)
        return [ChunkPiece(text=chunk, chunk_index=index, chunk_count=total) for index, chunk in enumerate(chunks)]

    def _looks_like_table(self, text: str, content_type: str | None) -> bool:
        if content_type and "table" in content_type.lower():
            return True
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        pipe_rows = sum(1 for line in lines if "|" in line)
        return len(lines) >= 2 and pipe_rows >= max(2, len(lines) // 2)

    def _split_table(self, text: str) -> List[str]:
        lines = [line.rstrip() for line in text.splitlines()]
        non_empty_lines = [line for line in lines if line.strip()]
        if not non_empty_lines:
            return []

        header_lines, row_lines = self._detect_table_header(non_empty_lines)
        if not row_lines:
            return [text]

        packed: List[str] = []
        current_rows: List[str] = []
        header_text = "\n".join(header_lines).strip()

        for row in row_lines:
            candidate_rows = current_rows + [row]
            candidate = self._format_table_chunk(header_lines, candidate_rows)
            if len(candidate) <= self.chunk_size:
                current_rows = candidate_rows
                continue

            if current_rows:
                packed.append(self._format_table_chunk(header_lines, current_rows))
                current_rows = [row]
            else:
                packed.extend(self._hard_split(row))
                current_rows = []

        if current_rows:
            packed.append(self._format_table_chunk(header_lines, current_rows))

        return [chunk for chunk in packed if chunk.strip()]

    def _detect_table_header(self, lines: Sequence[str]) -> tuple[List[str], List[str]]:
        if len(lines) < 2:
            return [], list(lines)

        first_line = lines[0]
        second_line = lines[1]
        if self._is_separator_row(second_line):
            return [first_line, second_line], list(lines[2:])

        if "|" in first_line:
            return [first_line], list(lines[1:])

        return [], list(lines)

    @staticmethod
    def _is_separator_row(line: str) -> bool:
        normalized = line.replace("|", "").replace(" ", "")
        return bool(normalized) and set(normalized) <= {"-", ":"}

    def _format_table_chunk(self, header_lines: Sequence[str], row_lines: Sequence[str]) -> str:
        parts = [line for line in header_lines if line.strip()]
        parts.extend(row for row in row_lines if row.strip())
        return "\n".join(parts).strip()

    def _split_by_paragraphs(self, text: str) -> List[str]:
        paragraphs = [paragraph.strip() for paragraph in text.split("\n\n")]
        return [paragraph for paragraph in paragraphs if paragraph]

    def _split_recursive(self, text: str) -> List[str]:
        for separator in ["\n", ". ", "; ", ", ", " "]:
            if separator in text:
                parts = self._split_and_pack(text, separator)
                if parts:
                    return parts
        return self._hard_split(text)

    def _split_and_pack(self, text: str, separator: str) -> List[str]:
        parts = [part.strip() for part in text.split(separator) if part.strip()]
        if not parts:
            return []

        packed: List[str] = []
        current = ""
        for part in parts:
            candidate = part if not current else f"{current}{separator}{part}"
            if len(candidate) <= self.chunk_size:
                current = candidate
                continue

            if current:
                packed.append(current)
                current = ""

            if len(part) <= self.chunk_size:
                current = part
            else:
                packed.extend(self._split_recursive(part))

        if current:
            packed.append(current)
        return packed

    def _hard_split(self, text: str) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]

        step = max(1, self.chunk_size - self.chunk_overlap)
        pieces: List[str] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + self.chunk_size)
            pieces.append(text[start:end].strip())
            if end >= len(text):
                break
            start += step
        return [piece for piece in pieces if piece]

    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        if not chunks:
            return []

        merged: List[str] = []
        current = chunks[0]
        for chunk in chunks[1:]:
            candidate = f"{current}\n\n{chunk}"
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                merged.append(current)
                current = chunk
        merged.append(current)
        return merged
