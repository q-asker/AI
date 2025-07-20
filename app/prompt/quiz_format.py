from app.dto.request.generate_request import QuizType
from app.prompt.core.blank import blank_quiz_format
from app.prompt.core.multiple import multiple_quiz_format
from app.prompt.core.ox import ox_quiz_format


def get_quiz_format(quiz_type: QuizType):
    if quiz_type == QuizType.OX:
        return ox_quiz_format
    elif quiz_type == QuizType.BLANK:
        return blank_quiz_format
    elif quiz_type == QuizType.MULTIPLE:
        return multiple_quiz_format
