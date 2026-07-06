# Hướng Dẫn Tích Hợp Hệ Thống Cấp Cứu (Backend & AI Service) Dành Cho Frontend Developer

Tài liệu này hướng dẫn cách cài đặt, khởi chạy các dịch vụ cơ sở hạ tầng, Spring Boot Backend, và FastAPI AI Service để lập trình viên Frontend (FE) có thể tích hợp và kiểm thử luồng nghiệp vụ từ khi người dùng bấm nút SOS/gọi điện cho đến khi hệ thống AI hoàn thành xử lý Triage phân loại khẩn cấp.

---

## 1. Tổng Quan Luồng Dữ Liệu & Nghiệp Vụ

```
[Người dùng (FE)] 
    │
    ├─► (1) Bấm SOS ──► POST /api/v1/calls/sos ──► [Spring Boot (8080)] 
    │                                                   │ (Lưu DB & Log)
    │                                                   ▼
    └─► (2) Gọi điện ─► POST /api/v1/calls/voice ─► [Spring Boot (8080)]
                                                        │
                                                        ├─► Đẩy audio lên MinIO (9000)
                                                        ├─► Ghi nhận DB & Audit Log
                                                        ├─► Đẩy job vào Redis Queue (6379)
                                                        │
                                                        ▼
                                                    [Redis Queue]
                                                        │
                                                        ▼ (BRPOP)
                                                [AI Worker (FastAPI)]
                                                        │
                                                        ├─► Tải file ghi âm từ MinIO
                                                        ├─► Chạy Whisper (Speech to Text)
                                                        ├─► Chạy LLM / Fallback Regex (Triage)
                                                        │
                                                        ▼ (Callback POST)
                                                [Spring Boot Backend]
                                                        │
                                                        ├─► Cập nhật DB (Status = ANALYZED)
                                                        │
                                                        ▼ (WebSocket Broadcast)
                                                [Điều phối viên (FE)] (ws-emergency)
```

---

## 2. Cài Đặt Các Phụ Thuộc Chung (Cơ Sở Hạ Tầng)

Trước khi chạy các project, cần khởi động các dịch vụ sau (khuyến khích chạy qua Docker để nhanh nhất):

### 2.1. PostgreSQL (Có hỗ trợ PostGIS)
- **Port**: `5432`
- **Database**: `semd_db`
- **Username / Password**: `postgres` / `123456`
- **Docker Command**:
  ```bash
  docker run --name semd-postgres -p 5432:5432 -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=123456 -e POSTGRES_DB=semd_db -d postgis/postgis:15-3.3
  ```

### 2.2. Redis (Hàng đợi công việc AI)
- **Port**: `6379`
- **Docker Command**:
  ```bash
  docker run --name semd-redis -p 6379:6379 -d redis:7.0-alpine
  ```

### 2.3. MinIO (Lưu trữ file ghi âm cuộc gọi)
- **Port API**: `9000` (Port Console/UI: `9001`)
- **Username / Password**: `admin` / `admin123456`
- **Docker Command**:
  ```bash
  docker run -p 9000:9000 -p 9001:9001 --name semd-minio -e "MINIO_ROOT_USER=admin" -e "MINIO_ROOT_PASSWORD=admin123456" -d minio/minio server /data --console-address ":9001"
  ```
- **Cấu hình Bucket (QUAN TRỌNG)**:
  1. Truy cập trang quản trị MinIO tại `http://localhost:9001` (đăng nhập bằng `admin` / `admin123456`).
  2. Tạo một bucket mới tên là: `ems-cad-audio`.
  3. Vào phần **Settings** / **Anonymous Rules** của bucket này, thêm quyền đọc công khai bằng cách thêm rule: 
     - Prefix: `*` (hoặc để trống)
     - Access Policy: `Read` hoặc `ReadOnly`
     *(Điều này giúp AI Service của Python có thể tự do tải file ghi âm từ link public do Spring Boot cung cấp qua HTTP GET).*

---

## 3. Cài Đặt Trình Khởi Chạy LLM Cục Bộ (LM Studio)

Để hệ thống AI nhận diện được rủi ro trong cuộc gọi bằng mô hình ngôn ngữ lớn (LLM):
1. Tải và cài đặt phần mềm **LM Studio** (phiên bản phù hợp với hệ điều hành).
2. Tải về và tải lên (Load) một mô hình ngôn ngữ hỗ trợ tốt tiếng Việt (ví dụ: `Qwen2.5-7B-Instruct-GGUF` hoặc `Llama-3-8B-Instruct` hoặc `Gemma-E4b`).
3. Chuyển sang mục **Developer / Local Server** trong LM Studio.
4. Bật Server ở cổng mặc định `1234`.
5. Đảm bảo API Endpoint `http://localhost:1234/v1` đã sẵn sàng hoạt động.

*Lưu ý: Nếu LM Studio ngoại tuyến hoặc chưa load mô hình, AI Service sẽ tự động chuyển sang sử dụng bộ luật từ khóa Regex dự phòng để đưa ra phân loại khẩn cấp (không làm ngắt luồng xử lý).*

---

## 4. Chạy Spring Boot Backend (`semd-backend`)

Dịch vụ này quản lý API nghiệp vụ, tương tác cơ sở dữ liệu, quản lý file qua MinIO, và phát tán WebSocket.

### Cài đặt & Khởi chạy:
1. Đảm bảo bạn đã cài đặt **Java 21** và **Maven**.
2. Di chuyển vào thư mục backend: `cd semd-backend`
3. Kiểm tra file cấu hình `src/main/resources/application.yaml` để đảm bảo các thông số kết nối Database, Redis, MinIO trùng khớp.
4. Khởi chạy dự án:
   ```bash
   mvn clean spring-boot:run
   ```
   *Spring Boot sẽ tự động chạy Flyway migration để tạo toàn bộ bảng trong CSDL (lên tới version 15).*
5. API Swagger Docs sẽ sẵn sàng tại: `http://localhost:8080/swagger-ui.html`

---

## 5. Chạy AI Service (`EMS CAD Thesis`)

Dịch vụ này bao gồm FastAPI Web API và Background Worker để nhận diện tiếng nói và đánh giá rủi ro (triage).

### Cài đặt & Khởi chạy:
1. Đảm bảo đã cài đặt **Python 3.10+**.
2. Di chuyển vào thư mục AI Service: `cd "EMS CAD Thesis"`
3. Tạo môi trường ảo và kích hoạt:
   ```bash
   python -m venv venv
   # Kích hoạt trên Windows:
   venv\Scripts\activate
   # Kích hoạt trên macOS/Linux:
   source venv/bin/activate
   ```
4. Cài đặt các thư viện phụ thuộc:
   ```bash
   pip install -r requirements.txt
   ```
5. Khởi chạy **FastAPI Server** (để cung cấp API trực tiếp nếu cần):
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
6. Khởi chạy **AI Worker** (để nghe hàng đợi Redis và tự động xử lý):
   ```bash
   python app/worker.py
   ```
   *Lần chạy đầu tiên, mô hình Speech-to-Text Whisper (`medium`) sẽ tự động được tải từ Hugging Face về máy (quá trình này mất khoảng vài phút).*

---

## 6. Hướng Dẫn Tích Hợp Cho Nhà Phát Triển Frontend (FE)

FE cần gọi 2 đầu API chính để giả lập thao tác của người báo cáo cấp cứu, đồng thời lắng nghe WebSocket để nhận kết quả phân tích thời gian thực từ điều phối viên.

### 6.1. API SOS (Khi người dùng bấm nút SOS)
FE gửi trực tiếp tọa độ của người dùng về Backend.

- **Endpoint**: `POST http://localhost:8080/api/v1/calls/sos`
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "reporterPhone": "0987654321",
    "reporterName": "Nguyễn Văn B",
    "latitude": 21.028511,
    "longitude": 105.804817
  }
  ```
- **Response** (HTTP 201 Created):
  ```json
  {
    "id": 1,
    "reporterPhone": "0987654321",
    "reporterName": "Nguyễn Văn B",
    "status": "SOS",
    "longitude": 105.804817,
    "latitude": 21.028511,
    "createdAt": "2026-07-06T16:00:00"
  }
  ```

### 6.2. API Gửi Cuộc Gọi Thoại (Khi người dùng gọi điện cấp cứu)
FE thu âm file ghi âm và gửi kèm tọa độ của người dùng lên Backend.

- **Endpoint**: `POST http://localhost:8080/api/v1/calls/voice`
- **Content-Type**: `multipart/form-data`
- **Request Parameters**:
  - `reporterPhone`: Số điện thoại người gọi (String, ví dụ `0912345678`)
  - `reporterName`: Tên người gọi (String, không bắt buộc, ví dụ `Nguyễn Văn A`)
  - `latitude`: Vĩ độ tọa độ GPS (Double, ví dụ `21.022`)
  - `longitude`: Kinh độ tọa độ GPS (Double, ví dụ `105.838`)
  - `file`: File ghi âm âm thanh dạng `.wav`, `.mp3`, hoặc `.m4a` (MultipartFile)
- **Response** (HTTP 202 Accepted):
  ```json
  {
    "id": 2,
    "reporterPhone": "0912345678",
    "reporterName": "Nguyễn Văn A",
    "audioUrl": "http://localhost:9000/ems-cad-audio/random-uuid.wav",
    "status": "RECEIVED",
    "longitude": 105.838,
    "latitude": 21.022,
    "createdAt": "2026-07-06T16:05:00"
  }
  ```

### 6.3. Đón Kết Quả Phân Tích Thực Tế Qua WebSocket
Để màn hình điều phối viên cập nhật trạng thái tự động mà không cần tải lại trang:
1. FE kết nối WebSocket (STOMP Client) tới địa chỉ: `ws://localhost:8080/ws-emergency`.
2. Đăng ký nhận tin nhắn (Subscribe) từ Topic: `/topic/calls`.
3. **Sự kiện nhận được**:
   - Khi có bất kỳ cuộc gọi SOS hoặc Voice mới được tạo, Backend sẽ phát tin nhắn chứa thông tin ban đầu lên topic này.
   - Khi AI Service hoàn thành việc dịch text và phân loại mức độ khẩn cấp (Triage), nó sẽ gửi callback về Backend. Backend cập nhật trạng thái cuộc gọi thành `"ANALYZED"` và **phát tin nhắn cập nhật mới nhất chứa kết quả phân tích** lên topic `/topic/calls`.
   - **Cấu trúc tin nhắn kết quả nhận từ WebSocket**:
     ```json
     {
       "id": 2,
       "reporterPhone": "0912345678",
       "reporterName": "Nguyễn Văn A",
       "audioUrl": "http://localhost:9000/ems-cad-audio/random-uuid.wav",
       "aiTranscript": "Alo, cấp cứu à! Bố tôi tự nhiên bị đau ngực dữ dội, khó thở...",
       "aiUrgencyPrediction": "HIGH",
       "aiConfidenceScore": 95.0,
       "status": "ANALYZED",
       "longitude": 105.838,
       "latitude": 21.022,
       "createdAt": "2026-07-06T16:05:00"
     }
     ```
     *Dựa trên trường `aiUrgencyPrediction` (LOW, MEDIUM, HIGH, CRITICAL), FE có thể hiển thị cảnh báo màu sắc tương ứng trên màn hình của điều phối viên.*
