# Hướng dẫn cho editor

Công cụ này nhận **thư mục tập** (kịch bản `.xlsx` + lời thoại + footage) và trả về **timeline Premiere**
(`.xml`) đã dựng sẵn theo đúng kiểu dựng của kênh. Việc của editor là chuẩn bị đúng thư mục tập, bấm dựng,
rồi mở XML trong Premiere và hoàn thiện.

Chi tiết kỹ thuật ở `README.md`. File này chỉ là việc hằng ngày.

---

## 1. Cài trên máy — làm một lần

Cắm ổ SAM, mở Terminal, dán nguyên dòng này:

```bash
cd "/Volumes/SAM/0-SAM ASSET/MAVA AUTO EDIT" && make setup
```

Chạy khoảng 5–10 phút (cài ffmpeg, whisper, môi trường Python, model nhận giọng nói 141 MB). Máy nào chưa
chạy lệnh này thì công cụ không chạy được — môi trường nằm ở `~/.auto-edit-venv`, riêng từng máy, không nằm
trên ổ SAM.

Xong rồi thì không cần chạy lại, kể cả khi công cụ được cập nhật.

---

## 2. Chuẩn bị thư mục tập

Thư mục tập **phải nằm trong thư mục của kênh** thì công cụ mới biết tập này của kênh nào:

```
/Volumes/SAM/0-EARTHCUE/…      /Volumes/SAM/0-TRIPINSIGHT/…
/Volumes/SAM/0-DOCSUNTOLD/…    /Volumes/SAM/0-CHASELAND/…
```

Bên trong cần đủ 3 thứ:

| Thứ | Ở đâu | Lưu ý |
|---|---|---|
| Kịch bản `.xlsx` | bất kỳ đâu trong thư mục tập | phải có sheet tên **Content** |
| Footage | `VIDEO/` | tên file đúng như cột `File name EN` trong kịch bản |
| Lời thoại | `AUDIO/`, `EN/AUDIO/` hoặc `EN/AUDIO EN/` (tuỳ kênh) | xem cách đặt tên bên dưới |

### Đặt tên file lời thoại

Tên file = **số thứ tự + tên section** đúng như trong kịch bản, rồi tới mã ngôn ngữ và số phần:

```
1. Sydney Harbour 1.mp3          2. Little Rock en 1.mp3
5. Devil_s Den State Park 2.mp3  11. Malmo 1.mp3
```

Ba điều hay sai:

- **Dấu** — kịch bản ghi `Malmö`, file ghi `Malmo` vẫn khớp. Yên tâm.
- **Dấu câu** — kịch bản ghi `Devil's Den`, file ghi `Devil_s Den` vẫn khớp.
- **Sau tên section chỉ được có mã ngôn ngữ và số.** `8. Fayetteville en 1.mp3` là của section
  *Fayetteville*, không phải *Fayetteville National Cemetery*. Thêm chữ lạ vào là trượt.

> Không có file `QUIZ …` riêng cũng được: nếu phần quiz được đọc liền ở cuối file lời thoại của đoạn
> trước, công cụ tự cắt ra ở chỗ im lặng trước câu hỏi. Cùng cách đó cho mọi đoạn thiếu file riêng.

### Ba cái bẫy

- **Không để file `.xlsx` thừa trong thư mục tập.** Sao lưu kịch bản thì đổi đuôi thành `.xlsx.bak`, nếu
  không công cụ có thể quét trúng bản cũ.
- **Không để lời thoại trong thư mục con** kiểu `AUDIO EN/drive-download-…/` — kéo hết lên thư mục gốc.
- **Không để hai file lời thoại trùng tên** (`… (1).mp3`). Bản không dùng thì chuyển ra ngoài.

---

## 3. Dựng

Cách dễ nhất: mở thư mục `MAVA AUTO EDIT` trong Claude Code rồi nói, kèm đường dẫn thư mục tập:

> dựng tập /Volumes/SAM/0-EARTHCUE/260912 Earthcue - Sierra Nevada

Hoặc gõ `/edit <đường dẫn tập>`.

Tự chạy Terminal cũng được:

```bash
cd "/Volumes/SAM/0-SAM ASSET/MAVA AUTO EDIT"
```

```bash
./autoedit edit "/Volumes/SAM/0-EARTHCUE/260912 Earthcue - Sierra Nevada"
```

Lần đầu mất vài phút vì phải nhận dạng giọng nói; các lần sau nhanh hơn vì đã lưu lại.

Dựng xong sẽ báo: độ dài, số shot, số câu thoại, và **cảnh báo**. Đọc cảnh báo, đừng bỏ qua — hay gặp nhất
là *V1 trống x giây từ phút y*, nghĩa là footage ngắn hơn lời thoại, chỗ đó sẽ đen màn hình, cần thay
footage dài hơn hoặc bù clip trong Premiere.

---

## 4. Mở trong Premiere

File `.xml` nằm ngay trong thư mục tập (riêng Tripinsight nằm trong `EN/`).

1. Premiere → **File → Import…** → chọn file `.xml`.
2. Nếu Premiere hỏi **Link Media** → chỉ tới thư mục `VIDEO` của tập.

Trong project sẽ có:

- bin **SOURCE** (ASSET, VIDEO, AUDIO, SOUND)
- bin **SEQUENCE**: mỗi phần một sequence, và **FINAL** lồng tất cả các phần — đã có lower third, logo,
  nhạc nền.

Làm việc trên FINAL. Thêm SFX, chỉnh nhịp, thay footage thoải mái.

> Nếu Premiere **không import được gì cả**, đừng sửa tay — báo lại kèm đường dẫn file để kiểm tra.
> Thường là một clip vượt quá độ dài sequence, Premiere từ chối cả file mà không báo lỗi.

---

## 5. Bản ES / PT

Chỉ Tripinsight (ES, PT) và Earthcue (ES) có bản ngôn ngữ.

**Làm bản EN trước, hoàn thiện trong Premiere trước, rồi mới làm bản ngôn ngữ.** Vì công cụ đọc file
`.prproj` của bạn để **mang theo SFX bạn đã thêm** — dịch và giãn đúng theo độ dài lời thoại mới.

Cần có: lời thoại ngôn ngữ đó trong `<tập>/ES/AUDIO ES/` (hoặc `<tập>/ES/AUDIO/`; `PT` tương tự), và
file `.prproj` bản EN đã lưu trong `<tập>/EN/`.

> làm bản ES của tập Colombia

hoặc:

```bash
./autoedit lang "/Volumes/SAM/0-TRIPINSIGHT/260414 Tripinsight - Colombia" ES
```

Ra `<tập>/ES/<tên ES>.xml`. Lower third, logo, ending, quiz đều đã đổi sang ngôn ngữ đó.

Hai điều cần biết:
- **Gain, fade và effect của SFX không mang theo** — chỉ vị trí và độ dài. Chỉnh lại trong Premiere.
- Tripinsight ES **cố tình không có Subscribe**; editor tự thêm MOGRT `SUB ES`.

---

## 6. Sửa một tập đã dựng

Nói chỗ sai, chụp màn hình Premiere kéo vào cũng được:

> chỗ subscribe bị lệch sang trái
> /fix lower third tập Colombia hiện quá sớm

Sửa kịch bản hoặc thay footage rồi muốn dựng lại:

```bash
./autoedit rebuild "<tập>"
```

---

## 7. Lỗi hay gặp

| Báo gì | Làm gì |
|---|---|
| `no .xlsx with a 'Content' sheet` | kịch bản thiếu, hoặc sheet không tên `Content` |
| `no EN/AUDIO folder` | thư mục lời thoại sai tên hoặc chưa có |
| không biết tập thuộc kênh nào | thư mục tập chưa nằm trong `/Volumes/SAM/0-<KÊNH>/` |
| thiếu footage `126-…` | tên trong cột `File name EN` không khớp file trong `VIDEO/` |
| Premiere không import | chạy `./autoedit check "<file.xml>"` rồi gửi kết quả |
| lệnh không chạy, `command not found` | máy này chưa `make setup` |

Kiểm tra file XML bất cứ lúc nào:

```bash
./autoedit check "/Volumes/SAM/0-EARTHCUE/260912 Earthcue - Sierra Nevada/260912 Earthcue - Sierra Nevada.xml"
```

---

## Không tự làm

- **Không copy công cụ vào thư mục tập.** Một bộ dùng chung cho mọi kênh, nằm ở
  `/Volumes/SAM/0-SAM ASSET/MAVA AUTO EDIT`.
- **Không sửa file trong `engine/`, `channels/`, `skills/`.** Cần đổi kiểu dựng (khoảng nghỉ, font, vị trí
  chữ, thời lượng lower third) thì báo — đổi là đổi cho tất cả các kênh.
- **Render video** (`final`, `preview`) chỉ chạy khi thật sự cần: mất bằng thời lượng tập. Bình thường chỉ
  cần timeline.
