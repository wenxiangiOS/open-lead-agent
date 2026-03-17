from src.services.data.extraction_service import ExtractionService


def test_normalize_extracted_value_filters_placeholder_values():
    assert ExtractionService._normalize_extracted_value("值") is None
    assert ExtractionService._normalize_extracted_value("值/null") is None
    assert ExtractionService._normalize_extracted_value("null（电话号码）") is None
    assert ExtractionService._normalize_extracted_value("程序员") == "程序员"


def test_normalize_extracted_value_filters_valuenull_variant():
    """测试 '值null' 占位符变体（无斜杠）被正确过滤"""
    # AI 可能误抄模板内容，返回 "值null" 而不是 "值/null"
    assert ExtractionService._normalize_extracted_value("值null") is None
    assert ExtractionService._normalize_extracted_value("值Null") is None
    assert ExtractionService._normalize_extracted_value("值NULL") is None
    # 其他"值"开头的短占位符也应该被过滤
    assert ExtractionService._normalize_extracted_value("值xxx") is None
    assert ExtractionService._normalize_extracted_value("值示例") is None
    # 正常的职业名称应该保留
    assert ExtractionService._normalize_extracted_value("工程师") == "工程师"
    assert ExtractionService._normalize_extracted_value("教师") == "教师"

