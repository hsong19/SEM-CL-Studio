# SEM-CL Studio

Python/PySide6 기반 SEM-CL HDF5 mapping 및 spectrum 분석 프로그램의 초기 실행 버전입니다.

## 처음 사용하는 분

GitHub와 VS Code가 익숙하지 않다면 아래 안내서를 순서대로 따라 하세요.

**[VS Code로 GitHub에서 내려받아 실행하는 방법](VS_CODE_USER_GUIDE.md)**

저장소를 VS Code로 Clone한 뒤 권장 확장을 설치하면 `F5`로 바로 실행할 수 있습니다.

## 현재 구현된 기능

- 여러 HDF5 파일 불러오기 및 drag & drop
- 선택 파일의 Survey/Concurrent SE 이미지 표시
- voltage, beam current, magnification, exposure metadata 표시
- total, single-wavelength, wavelength-band CL mapping
- 평균 spectrum에서 wavelength point/range 설정
- colormap, colorbar, scale bar 및 SE overlay
- Spectrum 탭의 CL map 직접 point 선택
- point별 원형 marker와 spectrum line 색상 연동
- point 색상 변경, 이름 변경, sampling 크기 선택
- spectrum Overlay/Stack 및 Auto/Manual offset
- figure clipboard 복사와 PNG/PDF/SVG export
- spectrum data clipboard 복사

원본 HDF5 파일은 항상 읽기 전용으로 사용합니다.

## 실행

Python 3.11 이상과 [uv](https://docs.astral.sh/uv/)가 권장됩니다.

```powershell
uv sync
uv run semcl-studio
```

또는 환경에 dependency가 설치되어 있다면:

```powershell
python app.py
```

HDF5 파일을 명령행에서 바로 열 수도 있습니다.

```powershell
uv run semcl-studio .\data\Control_5kV230pA220mTorr_1.h5
```

## 테스트

```powershell
uv run pytest
```

상세 기능과 장기 계획은 `BLUEPRINT.md`, 시각 규칙은 `DESIGN.md`를 참고합니다.
