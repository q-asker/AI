from app.dto.request.generate_request import DOKLevel, QuizType
from app.prompt.core.blank import blank_quiz_guidelines
from app.prompt.core.multiple import multiple_quiz_guidelines
from app.prompt.core.ox import ox_guidelines


def get_quiz_generation_guide(dok_level: DOKLevel, quiz_type: QuizType):
    if quiz_type == QuizType.OX:
        return ox_guidelines.get(dok_level)
    elif quiz_type == QuizType.BLANK:
        return blank_quiz_guidelines.get(dok_level)
    elif quiz_type == QuizType.MULTIPLE:
        return multiple_quiz_guidelines.get(dok_level)
    else:
        raise ValueError(f"Unsupported quiz type: {quiz_type}")


def get_quiz_format(quiz_type: QuizType):
    if quiz_type == QuizType.OX:
        return "ox"
    elif quiz_type == QuizType.BLANK:
        return "blank"
    elif quiz_type == QuizType.MULTIPLE:
        return "multiple"
    else:
        raise ValueError(f"Unsupported quiz type: {quiz_type}")
