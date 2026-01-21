# AI
## FastAPI?
### 이벤트 루프 기반 비동기 웹 프레임워크
### 1. async def의 약속: "나 혼자 할게요"
async def를 쓴다는 건 개발자가 FastAPI에게 이렇게 말하는 것과 같습니다.

"이 함수는 제가 비동기로 잘 짰어요. 
멈추는 구간(논블로킹 I/O에서 await)에서 알아서 비켜줄 테니,메인 스레드에서 빠르게 실행해 주세요."

-> 비동기 I/O를 await로 호출시 별도의 큐로 빠져서 epoll을 통해 대기한다. 파이썬 자체의 기능이며 FastAPI가 제공하는 기능이 아님.

한편, 아래 코드는 await를 호출해도 CPU 타임을 할당받아 실행된다.
```python
async def generate_specific_explanation(
    specific_explanation_request: SpecificExplanationRequest,
):

    title = specific_explanation_request.title
    selections = specific_explanation_request.selections

    selection_text = ""
    for idx, s in enumerate(selections, start=1):
        answer_tag = "(정답)" if s.correct else ""
        selection_text += f"{idx}. {s.content} {answer_tag}\n"
```

금기 사항: 여기서 약속을 어기고 ```time.sleep()```이나 ```requests.get()``` 같은 블로킹 함수를 쓰면?

결과: 메인 스레드(이벤트루프, 사장님)가 멈춰버립니다. 대참사가 일어납니다.
블로킹 함수를 호출한 스레드는 그 함수가 끝날 때까지 기다려야 하므로,
블로킹 함수가 끝나기 전까지 다른 작업을 처리하지 못합니다.

### 2. def의 배려: "무거우면 말해요, 들어줄게"
반면, 그냥 def를 쓰면 FastAPI는 이렇게 생각합니다.

"어? 이건 async가 아니네? 블로킹 함수일 수도 있겠구나. 안전하게 별도 스레드(알바생)를 붙여줘야겠다."

동작: FastAPI는 일반 def로 선언된 엔드포인트는 **알아서 스레드 풀(run_in_executor)**로 보내서 실행합니다.

결과: def 안에서 time.sleep이나 requests를 써도, 메인 서버는 멈추지 않습니다. (알바생만 멈춤)