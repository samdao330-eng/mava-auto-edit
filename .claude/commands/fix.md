---
description: Sửa một tập đã dựng (hoặc MAVA AUTO EDIT) theo mô tả, rồi xuất lại XML Premiere
argument-hint: "<mô tả cần sửa>" [thư mục tập]
---

Sửa theo yêu cầu của người dùng bằng MAVA AUTO EDIT. Trả lời bằng tiếng Việt, ngắn gọn.

Yêu cầu: $ARGUMENTS

Thư mục MAVA AUTO EDIT: `{{AUTOEDIT}}` (nếu chưa được thay bằng đường dẫn thật thì là thư mục đang mở, nơi có
`AGENTS.md`). Đọc `AGENTS.md` ở đó, rồi làm đúng theo `skills/fix-episode.md` (Premiere không import được:
`skills/premiere-xml.md`). Mọi lệnh chạy qua `"{{AUTOEDIT}}/autoedit"`.
