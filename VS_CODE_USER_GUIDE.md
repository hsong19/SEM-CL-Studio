# VS Code로 SEM-CL Studio 내려받아 실행하기

이 문서는 GitHub와 VS Code를 처음 사용하는 Windows 사용자를 위한 안내서입니다.  
GitHub 계정은 없어도 공개 저장소를 내려받아 사용할 수 있습니다.

## 1. 처음 한 번만 설치할 프로그램

### 1-1. Visual Studio Code 설치

1. [Visual Studio Code 다운로드 페이지](https://code.visualstudio.com/download)를 엽니다.
2. `Windows` 설치 파일을 내려받아 실행합니다.
3. 기본 설정 그대로 설치합니다.

### 1-2. Git 설치

1. [Git for Windows](https://git-scm.com/download/win)를 내려받습니다.
2. 설치 프로그램을 실행하고 기본 설정 그대로 설치합니다.
3. 설치가 끝나면 VS Code를 완전히 종료한 뒤 다시 실행합니다.

### 1-3. uv 설치

`uv`는 프로그램에 필요한 Python과 라이브러리를 자동으로 준비합니다.

1. VS Code 상단 메뉴에서 `Terminal` → `New Terminal`을 누릅니다.
2. 화면 아래쪽 터미널에 다음 명령을 붙여넣고 Enter를 누릅니다.

```powershell
winget install --id=astral-sh.uv -e
```

3. 설치가 끝나면 VS Code를 다시 시작합니다.

## 2. GitHub에서 프로그램 내려받기

1. VS Code를 실행합니다.
2. 키보드에서 `Ctrl + Shift + P`를 누릅니다.
3. 입력창에 `Git: Clone`을 입력하고 선택합니다.
4. 다음 GitHub 주소를 붙여넣고 Enter를 누릅니다.

```text
https://github.com/hsong19/SEM-CL-Studio.git
```

5. 프로그램을 저장할 상위 폴더를 선택합니다.
   - 예: `문서` 또는 `바탕 화면`
   - `SEM-CL-Studio` 폴더는 VS Code가 자동으로 만듭니다.
6. 다운로드가 끝나면 오른쪽 아래 또는 위쪽에 나타나는 `Open`을 누릅니다.
7. `Do you trust the authors of the files in this folder?`가 나오면 저장소 주소를 확인하고 `Yes, I trust the authors`를 누릅니다.
8. 오른쪽 아래에 권장 확장 설치 안내가 나타나면 `Install` 또는 `Install All`을 누릅니다.

## 3. 실행 환경 준비하기

프로젝트에 VS Code 작업 설정이 포함되어 있으므로 명령을 직접 입력하지 않아도 됩니다.

1. `Ctrl + Shift + P`를 누릅니다.
2. `Tasks: Run Task`를 입력하고 선택합니다.
3. `SEM-CL: Setup`을 선택합니다.
4. 아래쪽 터미널에 작업 완료 메시지가 나올 때까지 기다립니다.

또는 VS Code 터미널에서 다음 명령을 직접 실행해도 됩니다.

```powershell
uv sync
```

처음 실행할 때는 Python과 필요한 라이브러리를 내려받기 때문에 시간이 걸릴 수 있습니다. `uv sync`가 오류 없이 끝나면 준비가 완료된 것입니다.

## 4. SEM-CL Studio 실행하기

가장 쉬운 실행 방법은 키보드에서 `F5`를 누르는 것입니다.

1. `F5`를 누릅니다.
2. 실행 구성을 묻는 경우 `SEM-CL Studio`를 선택합니다.
3. VS Code가 필요한 환경을 확인한 뒤 프로그램 창을 엽니다.

디버깅 없이 실행하려면 다음 방법도 사용할 수 있습니다.

1. `Ctrl + Shift + P`를 누릅니다.
2. `Tasks: Run Task`를 선택합니다.
3. `SEM-CL: Run`을 선택합니다.

또는 터미널에서 다음 명령을 실행합니다.

```powershell
uv run semcl-studio
```

SEM-CL Studio 창이 열리면 왼쪽의 `Open` 또는 상단의 `Open Files`를 눌러 `.h5` 또는 `.hdf5` 측정 파일을 선택합니다.

프로그램 폴더의 `run_semcl.bat` 파일을 Windows 파일 탐색기에서 더블클릭해도 실행할 수 있습니다. 단, `uv sync`를 한 번 완료한 이후 사용하는 것을 권장합니다.

## 5. 측정 데이터 사용하기

측정 데이터는 GitHub 저장소에 포함되어 있지 않습니다.

- HDF5 파일은 컴퓨터의 어느 폴더에 두어도 됩니다.
- 프로그램에서 `Open Files`를 누르고 해당 파일을 선택하면 됩니다.
- 필요하면 `SEM-CL-Studio` 안에 `data` 폴더를 직접 만들어 넣어도 됩니다.
- `data` 폴더와 HDF5 파일은 Git에서 자동으로 제외됩니다.

## 6. 새 버전으로 업데이트하기

개발자가 프로그램을 업데이트했다면 VS Code에서 프로젝트 폴더를 연 후 터미널에 다음 명령을 차례로 입력합니다.

```powershell
git pull
uv sync
```

그다음 다시 실행합니다.

```powershell
uv run semcl-studio
```

## 7. 자주 발생하는 문제

### `git`을 찾을 수 없다고 나오는 경우

Git 설치 후 VS Code를 완전히 종료하고 다시 실행합니다. 그래도 해결되지 않으면 Windows를 한 번 재시작합니다.

### `uv`를 찾을 수 없다고 나오는 경우

VS Code를 다시 시작한 뒤 다음 명령으로 설치 여부를 확인합니다.

```powershell
uv --version
```

명령이 계속 인식되지 않으면 1-3단계의 설치 명령을 다시 실행합니다.

### 프로그램 창이 열리지 않는 경우

터미널에서 다음 명령을 실행하고 표시되는 오류 메시지를 확인합니다.

```powershell
uv sync
uv run semcl-studio
```

### 데이터 파일이 보이지 않는 경우

파일 선택창 오른쪽 아래의 파일 형식이 `HDF5 files (*.h5 *.hdf5)`인지 확인합니다.

## 가장 짧은 실행 순서

이미 VS Code, Git, uv가 설치되어 있다면 다음 순서만 기억하면 됩니다.

```text
Ctrl+Shift+P
→ Git: Clone
→ GitHub 주소 붙여넣기
→ Open
→ 권장 확장 Install All
→ Ctrl+Shift+P
→ Tasks: Run Task
→ SEM-CL: Setup
→ F5
```
