from app.dto.request.generate_request import DOKLevel, QuizType
from app.prompt.core.blank import blank_quiz_dok_guidelines
from app.prompt.core.multiple import multiple_quiz_dok_guidelines
from app.prompt.core.ox import ox_guidelines, ox_additional_guidelines


def get_quiz_generation_guide(dok_level: DOKLevel, quiz_type: QuizType):
    if quiz_type == QuizType.OX:
        if dok_level not in ox_guidelines:
            raise ValueError(f"Unsupported DOK level for OX quiz: {dok_level}")
        return ox_guidelines.get(dok_level) + ox_additional_guidelines
    elif quiz_type == QuizType.BLANK:
        if dok_level not in blank_quiz_dok_guidelines:
            raise ValueError(f"Unsupported DOK level for blank quiz: {dok_level}")
        return blank_quiz_dok_guidelines.get(dok_level)
    elif quiz_type == QuizType.MULTIPLE:
        if dok_level not in multiple_quiz_dok_guidelines:
            raise ValueError(f"Unsupported DOK level for multiple quiz: {dok_level}")
        return multiple_quiz_dok_guidelines.get(dok_level)
    else:
        raise ValueError(f"Unsupported quiz type: {quiz_type}")
