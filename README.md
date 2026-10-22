# MAVA AUTO EDIT

Môi trường dựng tự động cho các kênh du lịch (Earthcue, Docs Untold, Tripinsight, Chaseland, …): từ thư mục
tập (kịch bản `.xlsx` + VO + footage) xuất ra timeline **Premiere Pro** (`.xml`) theo đúng kiểu dựng đã chốt.
Một bộ máy dùng chung cho mọi kênh; mỗi kênh chỉ khác asset trong `channels/<kênh>/channel.json`.

Cách dùng giống OM: mở thư mục này trong Claude Code (hoặc Codex) rồi nói việc cần làm —
"dựng tập /Volumes/SAM/0-EARTHCUE/…", "làm bản ES", "sửa chỗ subscribe" — hoặc dùng `/edit`, `/fix`.

## Cài trên máy mới (1 lần)

1. Cài Homebrew nếu chưa có: https://brew.sh
2. Cắm ổ SAM, mở Terminal:
   ```bash
   cd "/Volumes/SAM/0-SAM ASSET/MAVA AUTO EDIT" && make setup
   ```
   Cài `ffmpeg`, `whisper-cpp`, môi trường Python (`~/.auto-edit-venv`, riêng từng máy vì ổ SAM là exFAT),
   model nhận giọng nói (148 MB) nếu chưa có, và lệnh `/edit`, `/fix` cho Claude Code ở mọi thư mục.

## Lệnh

Kênh tự nhận theo thư mục tập (`/Volumes/SAM/0-EARTHCUE/…` → earthcue, …).

```bash
./autoedit edit    "<tập>" [--sections intro,1,quiz,2,outro]   # dựng bản EN  -> <tập>/<tên>.xml
./autoedit lang    "<tập>" ES                                   # bản ES / PT  -> <tập>/ES/<tên ES>.xml
./autoedit rebuild "<tập>"                                      # dựng lại sau khi sửa
./autoedit check   "<file.xml>"                                 # kiểm tra trước khi import Premiere
./autoedit final   "<tập>"                                      # render MP4 4K (≈ thời gian thực)
./autoedit channel "<tập>"                                      # tập này của kênh nào
```

Kết quả nằm trong thư mục tập (Tripinsight: trong `EN/`):
- `<tên>.xml` → Premiere: **File → Import…**. Có sẵn bin SOURCE (ASSET, VIDEO, AUDIO, SOUND) và SEQUENCE
  (mỗi phần một sequence, **FINAL** lồng các phần, có lower third, logo, nhạc). Nếu hỏi Link Media, chỉ tới `VIDEO`.
- `MEDIA/` nhạc nền đã dùng · `.autoedit/` (ẩn) đồ hoạ tự tạo và dữ liệu trung gian.

## Thư mục

| | |
|---|---|
| `AGENTS.md` | bộ định tuyến cho Claude / Codex: việc nào đọc hướng dẫn nào |
| `skills/` | hướng dẫn từng việc: dựng tập, bản ES/PT, sửa, lỗi import XML, kiểu dựng, thêm kênh |
| `channels/<kênh>/` | `channel.json` (asset, vị trí, thời lượng) + `NOTES.md` (đo từ tập nào, đặc điểm kịch bản) |
| `engine/` | script Python, font, model whisper — dùng chung mọi kênh |
| `tests/` | `check-xml.py` (kiểm tra XML), `regression.sh` (`make test`: dựng thử tập mẫu mọi kênh) |
| `autoedit` | lệnh chung |
| `logchat.md` | nhật ký các lần làm việc |

## Thêm kênh mới

Không copy bộ công cụ: tạo `channels/<kênh>/channel.json` + `NOTES.md` (xem `skills/new-channel.md`), hoặc nói
với Claude "thêm kênh X, tập mẫu ở …".

## Lỗi hay gặp

- **Premiere không import được XML** → `./autoedit check "<file.xml>"`; xem `skills/premiere-xml.md`.
- **Báo không biết tập thuộc kênh nào** → thư mục tập phải nằm trong `/Volumes/SAM/0-<KÊNH>/`, hoặc chạy với
  `AUTOEDIT_CHANNEL=<kênh>`.
- **Chưa cài máy này** → `make setup`.
