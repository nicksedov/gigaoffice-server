curl -X POST http://localhost:9060/api/ai/response \
  -H "Content-Type: application/json" \
  -d '{
    "ai_request_id": "31b75ed2-749c-48f3-99a2-c487557107b5",
    "text_response": "Тестовый ответ от GigaChat для проверки сохранения в базу данных",
    "rating": true,
    "comment": "Отличный результат, данные обработаны корректно"
  }'