# agent_tools.py
from datetime import datetime, timedelta


class MockLogger:
    """Mock สำหรับ student_request logger และรายงานสรุป"""
    
    def append_student_request(self, student_id: str, category: str, topic: str, details: str):
        return {
            'ok': True,
            'message': f'บันทึกคำร้อง {topic} ({category}) รหัสนักศึกษา {student_id} เรียบร้อย',
            'student_id': student_id,
            'category': category,
            'topic': topic,
            'details': details
        }
    
    def get_request_summary(self):
        return {'ok': True, 'message': 'สรุปรายการคำร้องนักศึกษา: ทั้งหมด 12 รายการ (อนุมัติแล้ว 9, รอพิจารณา 3)'}


request_logger = MockLogger()
summary_report = MockLogger()


def validate_student_request(student_id: str, category: str, topic: str, details: str):
    """🛡️ Validation Guardrail: ตรวจสอบความถูกต้องของข้อมูลคำร้องนักศึกษา"""
    s_id = str(student_id).strip()
    if not s_id or len(s_id) < 5:
        return 'invalid student_id'
    if not str(category).strip():
        return 'category required'
    if not str(topic).strip():
        return 'topic required'
    if not str(details).strip():
        return 'details required'
    return None


def log_student_request(student_id: str, category: str, topic: str, details: str):
    """Tool: บันทึกคำร้องหรือคำขอนักศึกษา"""
    err = validate_student_request(student_id, category, topic, details)
    if err:
        return {'ok': False, 'tool': 'log_student_request', 'error': f'Validation failed: {err}'}
    return request_logger.append_student_request(student_id, category, topic, details)


def get_request_summary():
    """Tool: สรุปสถานะรายการคำร้องนักศึกษา"""
    return summary_report.get_request_summary()


def send_alert(message: str):
    """Tool: ส่งแจ้งเตือนผ่าน Bot"""
    return {'ok': True, 'message': f'ส่งแจ้งเตือน: {message}'}


TOOL_REGISTRY = {
    'log_student_request': {
        'fn': log_student_request,
        'args': ('student_id', 'category', 'topic', 'details'),
        'coerce': {'student_id': str, 'category': str, 'topic': str, 'details': str}
    },
    'get_request_summary': {
        'fn': get_request_summary,
        'args': (),
        'coerce': {}
    },
    'send_alert': {
        'fn': send_alert,
        'args': ('message',),
        'coerce': {'message': str}
    }
}


def execute_tool(tool_name: str, kwargs: dict):
    """ตัวรัน Tool พร้อม type coercion และ error handling"""
    if tool_name not in TOOL_REGISTRY:
        return {'ok': False, 'error': f'Unknown tool: {tool_name}'}
    
    tool = TOOL_REGISTRY[tool_name]
    
    # Coerce types
    for k, v_type in tool['coerce'].items():
        if k in kwargs:
            try:
                kwargs[k] = v_type(kwargs[k])
            except Exception:
                return {'ok': False, 'error': f'Bad type for {k}'}
    
    # Execute function
    try:
        return tool['fn'](**{k: kwargs[k] for k in tool['args']})
    except Exception as e:
        return {'ok': False, 'error': str(e)}