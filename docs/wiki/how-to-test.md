# 테스트 방법

## 단위 테스트
unittest를 사용해서 프로젝트의 단위 테스트를 실행.

```
# run unittest directly
python -m unittest discover ./tests *test.py -v
```

## 통합 테스트
통합 테스트는 실제 거래소를 사용해서 테스트가 진행됩니다. 몇몇 테스트는 주피터 노트북을 사용해서 테스트가 가능하도록 하였습니다. `notebook` 폴더를 확인해 보세요.

```
# run unittest directly
python -m unittest integration_tests

# or
python -m unittest integration_tests.simulation_ITG_test
```

# How to test

## Unit test
Test project with unittest.

```
# run unittest directly
python -m unittest discover ./tests *test.py -v
```

## Integration test
Test with real trading market. Some integration tests are excuted via Jupyter notebook. It's good to run test flexible re-ordered.

You can find notebook files in `notebook` directory.

```
# run unittest directly
python -m unittest integration_tests

# or
python -m unittest integration_tests.simulation_ITG_test
```
