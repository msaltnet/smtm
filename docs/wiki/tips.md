# 개발팁

커밋을 생성하기 전에 아래 명령어를 사용하여 Jupyter notebook의 출력을 삭제하세요.

```bash
jupyter nbconvert --clear-output --inplace {file.ipynb}
#jupyter nbconvert --clear-output --inplace .\notebook\*.ipynb
```

시뮬레이션이나 데모 모드를 사용하는 경우, SimulationDataProvider는 업비트의 정보를 사용하므로, 시스템 시간의 타임존이 한국으로 설정되어야 합니다. 특히, 클라우트 리눅스의 경우 아래 명령어로 설정 할 수 있습니다.

```bash
timedatectl set-timezone 'Asia/Seoul'
```

원격 터미널에서 프로그램 실행 후 연결을 종료하더라도 프로그램이 종료되지 않도록 하기 위해서 `nohup`을 사용하는 방법이 있습니다. 표준 출력과 에러를 별도의 파일에 저장하며 백그라운드로 실행하기 위해서는 다음과 같이 실행하면 됩니다.

```bash
nohup python -m smtm --mode 3 --demo 1 > nohup.out 2> nohup.err < /dev/null &
```

# Tips

clear jupyter notebook output before make commit

```bash
jupyter nbconvert --clear-output --inplace {file.ipynb}
#jupyter nbconvert --clear-output --inplace .\notebook\*.ipynb
```

If you run simulation or demo mode, you should set timezone to 'Asia/Seoul' because smtm use Upbit trading information for simulation and demo. For Linux, below command is available.

```bash
timedatectl set-timezone 'Asia/Seoul'
```

For keeping smtm program process after terminating ssh connection, using `nohup` is recommended as below. Standard, error ouput is redirected to specific files.
```bash
nohup python -m smtm --mode 3 --demo 1 > nohup.out 2> nohup.err < /dev/null &
```
