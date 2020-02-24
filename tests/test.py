import unittest

def custom_function(file_name):
    with open(file_name, 'rt') as f:
        return sum(1 for _ in f)


# TestCase를 작성
class CustomTests(unittest.TestCase):

    def setUp(self):
        """테스트 시작되기 전 파일 작성"""
        self.file_name = 'test_file.txt'
        with open(self.file_name, 'wt') as f:
            f.write("""
            파이썬에는 정말 단위테스트 모듈이 기본으로 포함되어 있나요? 진짜?
            멋지군요!
            단위테스트를 잘 수행해보고 싶습니다!
            """.strip())

    def tearDown(self):
        """테스트 종료 후 파일 삭제 """
        try:
            os.remove(self.file_name)
        except:
            pass

    def test_runs(self):
        """단순 실행여부 판별하는 테스트 메소드"""

        custom_function(self.file_name)

    def test_line_count(self):
        self.assertEqual(custom_function(self.file_name), 3)

# 샘플 코드는 https://wikidocs.net/16107 에서 가져왔습니다!
