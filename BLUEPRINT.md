# SEM-CL Studio Blueprint

> 상태: 기능 구상 및 구현 기준 문서  
> 대상: Python 기반 Windows 데스크톱 프로그램  
> 기본 원칙: 원본 HDF5 파일은 읽기 전용으로 취급하고 모든 분석은 재현 가능하게 기록한다.

## 1. 프로그램 목표

여러 SEM-CL HDF5 파일을 한 번에 불러온 뒤, 선택한 파일의 SE 이미지와 CL hyperspectral data를 함께 탐색하고 mapping 및 spectrum plotting을 수행한다.

대표 작업 흐름은 다음과 같다.

```text
프로그램 실행
→ 여러 HDF5 파일 불러오기
→ 왼쪽 파일 목록에서 분석 파일 선택
→ SEM Image tab에서 SE 이미지 단독 확인 및 기본 분석
→ SE 이미지 종류 선택
→ 평균 CL spectrum에서 파장 또는 파장 범위 선택
→ CL map 생성 및 SE overlay 확인
→ 이미지에서 여러 point/ROI 선택
→ spectrum 추출 및 plotting
→ 그림과 수치 결과 저장
```

## 2. 예시 데이터 기준

현재 예시 파일은 공통적으로 다음 데이터를 포함한다.

- `Secondary electrons survey`: 넓은 영역의 Survey SE 이미지
- `Secondary electrons concurrent`: CL 측정과 동시에 취득한 SE 이미지
- `Spectrum`: CL hyperspectral cube
- CL cube의 기본 차원: 약 `1024 × 101 × 101` 또는 `1024 × 103 × 103`
- 파장 범위: 약 `460.06–886.77 nm`
- 파장 간격: 약 `0.418 nm`
- CL 공간 픽셀 크기: 파일에 따라 약 `40–97 nm`

HDF5 내부의 acquisition 번호만 고정해서 사용하지 않고 `Title`, 데이터 차원 및 dimension scale을 함께 확인해 데이터를 식별한다.

## 3. 전체 화면 구성

파일 선택은 항상 보여야 하므로 왼쪽에는 고정된 파일 패널을 둔다. Mapping tab의 중앙에는 SE image와 CL mapping을 위아래로 배치하고, 오른쪽에는 제어 패널과 average spectrum을 위아래로 배치한다.

Mapping 화면에서 가장 중요한 콘텐츠는 SE image와 CL mapping이다. 따라서 기본 창 크기에서 중앙 이미지 영역이 전체 작업 영역의 약 `65–70%`를 차지하도록 한다.

- 왼쪽 파일 패널: 약 `12–15%`
- 중앙 SE/CL 이미지 영역: 약 `65–70%`
- 오른쪽 제어 및 spectrum 패널: 약 `18–22%`
- 중앙 영역 내부: SE와 CL을 기본 `50:50` 높이로 배치
- 오른쪽 영역 내부: Controls 약 `65%`, Average Spectrum 약 `35%`

```text
┌────────────────────────────────────────────────────────────────────────────────────┐
│ File  Project  View  Help   [SEM Image] [Mapping] [Spectrum] [Compare] [Export]    │
├──────────────────┬──────────────────────────────────────┬──────────────────────────┤
│ Files            │ SE Image                             │ Controls                 │
│                  │                                      │ ├─ Data/SE source        │
│ ○ Control ...    │                                      │ ├─ CL mapping            │
│ ● NMA ...        ├──────────────────────────────────────┤ ├─ Display/Overlay       │
│ ○ S-NEA ...      │ CL Mapping                           │ └─ Point/ROI             │
│ ○ rac-NEA ...    │                                      ├──────────────────────────┤
│                  │                                      │ Average Spectrum         │
│                  │                                      │                          │
├──────────────────┴──────────────────────────────────────┴──────────────────────────┤
│ 상태 메시지 | 현재 좌표 | 현재 파장 | 계산 진행률                                   │
└────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 상단 메뉴와 tab

- `File`
  - HDF5 파일 추가
  - 폴더에서 파일 추가
  - 선택 파일 제거
  - 전체 파일 제거
  - 프로그램 종료
- `Project`
  - 새 프로젝트
  - 프로젝트 열기
  - 프로젝트 저장
- `View`
  - panel 표시/숨김
  - 화면 배치 초기화
  - theme 선택
- 주요 tab
  - `SEM Image`
  - `Mapping`
  - `Spectrum`
  - `Compare` — 후속 버전
  - `Export`

### 3.2 왼쪽 파일 패널

- 여러 `.h5` 파일을 동시에 추가할 수 있다.
- 한 번에 하나의 파일을 active file로 선택한다.
- 왼쪽 패널에는 파일 목록과 로딩 상태만 표시해 최대한 단순하게 유지한다.
- 선택한 파일의 metadata는 오른쪽 제어 패널의 접을 수 있는 `Metadata` section에 표시한다.
- 핵심 metadata는 가속전압, beam current, magnification 및 exposure time이다.
- 보조 metadata는 pressure, dwell time, pixel size, image resolution, wavelength range 및 장비 설정이다.
- HDF5에 저장된 magnification과 exposure time은 원본값으로 표시한다.
- HDF5에 명확한 필드가 없는 전압, 전류 및 압력은 파일명에서 자동 추출한다.
- 파일명에서 추출한 값은 사용자가 수정할 수 있고, HDF5 원본값과 구분해 표시한다.
- 현재 파일의 로딩 상태와 오류 여부를 표시한다.
- 다른 파일을 선택하면 Mapping과 Spectrum 화면이 해당 파일 기준으로 갱신된다.
- 이전 파일의 point, ROI, 표시 설정은 프로젝트 내에 유지한다.
- 긴 filename은 말줄임표로 표시하고 hover tooltip에 전체 경로를 보여준다.
- 선택된 파일은 색상뿐 아니라 굵은 테두리와 selection marker로 명확히 구분한다.
- 키보드 위/아래 방향키로 파일을 전환할 수 있다.
- loading 중에는 skeleton/placeholder와 진행률을 표시하고 중복 클릭을 막는다.
- 파일을 제거할 때 저장되지 않은 ROI나 분석 결과가 있을 경우에만 확인한다.

### 3.3 선택 파일 Metadata section

Metadata section은 오른쪽 제어 패널 안에 배치하며, 왼쪽 목록에서 현재 선택한 파일에 대해서만 갱신된다. 분석에 불필요한 sample-description field는 포함하지 않는다.

핵심 표시 항목:

- Accelerating voltage (`kV`)
- Beam current (`pA`)
- SE magnification (`×`)
- CL exposure time (`s`)

보조 표시 항목:

- Chamber pressure (`mTorr`)
- SE dwell time (`s` 또는 `µs`)
- Survey/Concurrent SE pixel size와 resolution
- CL map pixel size와 resolution
- Wavelength 시작값, 종료값, channel 수 및 간격
- Spectrometer, grating, slit, binning 및 detector temperature

표시값의 출처를 `HDF5`, `Filename`, `User`로 구분한다. HDF5 값은 읽기 전용으로 유지하고, 파일명에서 추출한 값과 사용자 보정값만 프로젝트 파일에 저장한다.

### 3.4 사용자 친화적 GUI 원칙

프로그램을 처음 사용하는 사람도 별도 설명 없이 기본 분석을 수행할 수 있게 한다.

- HDF5 파일을 창에 drag & drop해서 추가할 수 있다.
- 자주 쓰는 기능은 화면에 보이는 버튼으로 제공한다.
- 세부 설정은 접을 수 있는 advanced section에 배치한다.
- 모든 icon button에는 이름과 tooltip을 표시한다.
- 현재 선택한 파일, SE source, wavelength range 및 처리 상태를 항상 표시한다.
- 긴 계산에는 progress bar와 cancel button을 제공한다.
- 오류 메시지는 원인과 해결 방법을 짧고 구체적으로 표시한다.
- 잘못된 숫자 입력은 즉시 강조하고 허용 범위를 안내한다.
- 변경된 값 옆에 reset button을 제공한다.
- 주요 화면에는 빈 화면 안내 문구를 제공한다.
  - 예: `왼쪽에서 HDF5 파일을 추가하거나 여기로 끌어오세요.`
- 최근 사용한 파일과 프로젝트를 다시 열 수 있다.
- keyboard shortcut과 우클릭 context menu를 함께 제공한다.
- status bar에 cursor 좌표, intensity, wavelength 및 작업 결과를 표시한다.

기본 단축키:

- `Ctrl+O`: 파일 추가
- `Ctrl+S`: 프로젝트 저장
- `Ctrl+C`: 현재 선택된 이미지, plot 또는 table 복사
- `Ctrl+Shift+C`: 현재 plot/map의 수치 데이터 복사
- `Ctrl+E`: Export dialog
- `Ctrl+Z` / `Ctrl+Y`: 사용자 조작 undo/redo
- `F`: Focus View
- `R`: 현재 view 초기화

### 3.5 Clipboard 복사·붙여넣기

SEM image, CL map, spectrum plot 및 결과 table을 다른 프로그램으로 즉시 복사할 수 있게 한다.

공통 동작:

- 각 결과 영역의 우측 상단에 `Copy` button을 둔다.
- 결과 위에서 우클릭하면 `Copy Image`, `Copy Data`, `Export...`를 표시한다.
- `Ctrl+C`는 현재 focus가 있는 결과를 자동으로 판단해 복사한다.
- 복사 완료 후 status bar에 결과와 형식을 표시한다.

이미지 및 plot 복사:

- 화면 screenshot이 아니라 title, axis, color bar 및 scale bar가 반영된 깨끗한 렌더링 결과를 복사한다.
- Windows clipboard에는 기본적으로 고해상도 PNG image를 저장한다.
- 투명 배경 여부와 복사 해상도를 설정할 수 있다.
- PowerPoint, Word, 메신저 및 이미지 편집기에 바로 붙여넣을 수 있게 한다.

수치 데이터 복사:

- spectrum은 `wavelength<TAB>intensity` 형식으로 복사한다.
- point/ROI가 여러 개이면 각 spectrum을 별도 column으로 복사한다.
- map 결과는 선택 영역 또는 전체 array를 tab-separated table로 복사한다.
- metadata와 결과 table은 header를 포함해 Excel에 바로 붙여넣을 수 있게 한다.
- 데이터가 지나치게 크면 전체 clipboard 복사 대신 CSV export를 안내한다.

### 3.6 공통 탐색 및 확대·축소 규칙

SEM Image, Mapping 및 Spectrum tab에서 가능한 한 같은 마우스·키보드 규칙을 사용한다. 사용자가 현재 tool mode를 추측하지 않도록 각 image/plot 상단에 compact navigation toolbar를 둔다.

```text
[Pointer] [Pan] [Zoom Box] [Point] [ROI] [Measure] | [Fit] [1:1] [Link] [Reset]
```

Tool mode:

- 한 번에 하나의 편집 tool만 활성화한다.
- 활성 tool은 눌린 button, cursor 모양 및 status text로 동시에 표시한다.
- `Esc`를 누르면 진행 중인 선택을 취소하고 기본 `Pointer` mode로 돌아간다.
- `Pan` 중에는 point나 ROI가 생성되지 않는다.
- `Point`, `ROI`, `Measure` mode에서만 해당 object를 생성한다.
- object를 선택하면 handle과 delete/rename action을 표시한다.

Mouse 동작:

- Mouse wheel: cursor 위치를 중심으로 부드럽게 zoom in/out
- Middle-button drag 또는 `Space + Left drag`: tool mode와 관계없이 임시 pan
- Left drag: 현재 선택된 tool 동작
- Right click: 현재 view에 맞는 context menu
- Double click: 전체 데이터가 보이도록 `Fit to View`
- 축 위에서 drag/wheel할 때는 해당 축만 조절하고, image 위에서는 x/y 비율을 유지한다.

Zoom 동작:

- 확대 시 cursor 아래의 데이터 위치가 화면에서 움직이지 않게 한다.
- image aspect ratio와 실제 물리 좌표 비율을 유지한다.
- 지나친 확대/축소를 막는 합리적인 minimum/maximum zoom을 둔다.
- `Fit`: 전체 image/data가 panel 안에 들어오게 표시한다.
- `1:1`: image 1 pixel을 screen 1 pixel로 표시한다.
- `Reset`: zoom, pan 및 display range를 해당 view의 기본값으로 복원한다.
- 새 파일을 처음 열 때는 Fit을 적용하고, 다시 돌아온 파일은 마지막 view 상태를 복원한다.
- tab을 바꾸거나 panel을 접어도 파일별 zoom/pan 상태를 유지한다.

Keyboard 동작:

- `+` / `-`: zoom in/out
- `0`: Fit to View
- `1`: 1:1 view
- 방향키: 작은 거리 pan
- `Shift + 방향키`: 큰 거리 pan
- `Delete`: 선택한 point/ROI/measurement 삭제
- `Esc`: 현재 tool 취소

### 3.7 SE–CL 연동 탐색

- `Link Views`가 켜져 있으면 SE image와 CL map의 물리 좌표 중심 및 view range를 동기화한다.
- 한쪽에서 zoom/pan하면 다른 쪽이 같은 물리 영역을 표시한다.
- 한쪽을 클릭하거나 hover하면 다른 쪽에도 같은 위치의 crosshair를 표시한다.
- 두 영상의 field of view가 다르면 겹치는 범위만 연동하고, 범위 밖 위치는 명확히 표시한다.
- 연결 상태는 두 panel 사이의 link icon으로 표시한다.
- Survey SE, Concurrent SE 및 CL map마다 pixel 크기가 다르므로 pixel index가 아닌 `µm` 기반 좌표로 연동한다.
- 연동이 불가능한 metadata 상태에서는 Link button을 비활성화하고 이유를 tooltip으로 알려준다.

### 3.8 반응성과 접근성

- 모든 panel은 Windows display scaling과 high-DPI monitor를 지원한다.
- 기본 글꼴 크기는 작게 고정하지 않고 시스템 설정을 따른다.
- 색상만으로 상태를 구분하지 않고 icon, line style 또는 text를 함께 사용한다.
- 기본 colormap은 색각 이상에도 비교적 안전한 `viridis` 또는 `cividis`를 사용한다.
- Light/Dark theme 모두에서 text, marker, ROI 및 color bar contrast를 확인한다.
- 계산 중에도 zoom, pan 및 tab 전환 등 읽기 전용 조작은 가능한 한 유지한다.
- 연속 slider/drag 입력은 debounce하여 불필요한 재계산과 화면 끊김을 방지한다.
- 계산이 끝난 뒤 view 중심과 zoom을 임의로 변경하지 않는다.

## 4. SEM Image 화면

HDF5에 포함된 SE 이미지만 크게 표시하고 기본적인 이미지 분석과 저장을 수행하는 독립 tab이다. CL mapping을 만들지 않아도 사용할 수 있으며, 왼쪽 파일 목록에서 선택한 파일 기준으로 즉시 갱신된다.

```text
┌──────────────────┬──────────────────────────────────────────────┬─────────────────┐
│ FILES            │ SEM IMAGE                                    │ SEM CONTROLS    │
│                  │                                              │ Image source    │
│ ○ File 1         │                                              │ Contrast/Invert │
│ ● File 2         │                                              │ Histogram       │
│ ○ File 3         │                                              │ Scale bar       │
│                  │                                   scale bar │ Measure/ROI     │
└──────────────────┴──────────────────────────────────────────────┴─────────────────┘
```

SE image source:

- `Survey SE`
- `Concurrent SE`

기본 기능:

- image source 전환
- 공통 navigation toolbar를 이용한 확대/축소, pan, Fit, 1:1 및 view 복원
- intensity 최소/최대값 조절
- percentile 기반 auto contrast
- grayscale 반전
- intensity histogram 표시
- 실제 pixel size를 이용한 scale bar
- 두 점 사이의 거리 측정
- Rectangle ROI의 폭, 높이 및 평균 intensity 표시
- cursor의 pixel 좌표, 물리 좌표 및 intensity 표시
- 화면 또는 원본 해상도 기준 이미지 저장
- 현재 SEM image를 clipboard에 복사
- PNG, TIFF, SVG/PDF figure export

SEM Image tab에서 만든 ROI와 측정 위치는 같은 파일의 Mapping tab에서도 선택적으로 표시할 수 있다. 자동 segmentation, particle counting 및 복잡한 morphology 분석은 초기 범위에서 제외한다.

## 5. Mapping 화면

Mapping 화면은 프로그램의 기본 화면이다.

```text
┌──────────────────┬─────────────────────────────────────┬───────────────────────────┐
│ FILES            │ SE IMAGE                            │ CONTROLS                  │
│                  │                                     │ SE source [Concurrent ▼] │
│ ○ File 1         │                                     │ CL mode   [Band ▼]       │
│ ● File 2         │                          scale bar  │ Range [700]–[800] nm     │
│ ○ File 3         ├─────────────────────────────────────┤ Colormap [viridis ▼]     │
│                  │ CL MAPPING                          │ Color bar [ON]           │
│                  │                                     │ Scale bar [ON]           │
│                  │                                     │ Overlay   [ON]           │
│                  │                    color/scale bar  │ Point / ROI controls     │
│                  │                                     ├───────────────────────────┤
│                  │                                     │ AVERAGE SPECTRUM          │
│                  │                                     │    선택 파장/범위         │
│                  │                                     │ └────────────── λ (nm)   │
└──────────────────┴─────────────────────────────────────┴───────────────────────────┘
```

세 영역의 폭과 SE/CL 및 Controls/Spectrum의 높이는 splitter로 조절할 수 있다. 중앙 이미지 영역에는 최소 폭을 지정해 양쪽 보조 패널을 넓혀도 SE/CL이 지나치게 작아지지 않게 한다.

- 왼쪽 파일 패널은 좁게 유지하며 collapse/expand할 수 있다.
- 오른쪽 제어 패널도 collapse/expand할 수 있다.
- `Focus View` 버튼으로 양쪽 패널을 동시에 숨기고 SE/CL만 크게 볼 수 있다.
- `Reset Layout`으로 권장 기본 비율을 복원한다.
- 창 크기를 변경할 때 남는 공간은 우선 중앙 SE/CL 영역에 배정한다.
- Average Spectrum은 파장 선택에 필요한 높이만 사용하고 이미지 영역을 침범하지 않는다.

### 5.1 오른쪽 제어 패널

오른쪽 위 제어 패널에 Mapping 화면의 조작 기능을 모은다. 기능이 많아지면 section을 접고 펼칠 수 있게 한다.

제어 패널은 고정 폭에 가까운 좁은 형태로 설계하고, 세부 옵션은 accordion/scroll 방식으로 제공한다. 옵션 증가 때문에 중앙 이미지 영역이 줄어들지 않게 한다.

- `Data`
  - SE source
  - CL mapping mode
  - wavelength point/range 숫자 입력
- `Display`
  - SE/CL intensity range
  - colormap과 color bar
  - scale bar
- `Overlay`
  - on/off
  - source, opacity 및 blending mode
- `Selection`
  - point/ROI tool
  - 선택 목록과 삭제
- `Metadata`
  - 선택 파일의 핵심 및 보조 측정조건
- `Reset`
  - view 또는 display setting 초기화

### 5.2 SE 이미지 패널

SE 이미지 종류를 combobox 또는 radio button으로 선택한다.

SE 패널과 CL 패널은 Mapping 화면에서 가장 넓은 영역을 사용하며, 이미지의 aspect ratio를 유지한 상태에서 가능한 크게 표시한다.

- `Survey SE`
- `Concurrent SE`

필수 조작 기능:

- 공통 navigation toolbar 기반 확대/축소와 pan
- Fit, 1:1 및 view reset
- contrast 자동 조정
- intensity 최소/최대 직접 입력
- grayscale 반전
- 이미지 저장
- scale bar 표시

Concurrent SE와 CL map은 단순히 픽셀 수에 맞춰 겹치지 않고 HDF5의 물리 좌표, pixel size, offset 및 rotation 정보를 이용해 정렬한다.

### 5.3 평균 CL spectrum

- CL cube 전체 공간의 평균 spectrum을 오른쪽 제어 패널 아래에 작은 그래프로 항상 표시한다.
- 전체 spectrum 형태와 선택 파장/range가 식별되는 범위에서 높이를 최소화한다.
- 필요하면 `Expand Spectrum` 버튼으로 일시 확대하고 다시 원래 크기로 복원한다.
- 왼쪽에서 파일을 선택하면 해당 파일의 average spectrum으로 즉시 갱신된다.
- x축 기본값은 wavelength `nm`이다.
- 선택적으로 photon energy `eV`로 전환할 수 있다.
- 마우스 hover 시 파장과 intensity를 표시한다.
- wheel zoom, drag pan, Fit 및 x축 range reset을 지원한다.
- 선택 wavelength와 실제 channel index를 함께 표시한다.
- 선택 방식은 두 가지로 구분한다.

#### Point wavelength mode

- spectrum에서 한 지점을 클릭한다.
- 가장 가까운 실제 wavelength channel을 선택한다.
- 선택 파장 한 채널 또는 설정한 인접 채널 평균으로 CL map을 생성한다.
- 현재 선택값을 숫자로 직접 입력할 수도 있다.
- 좌우 방향키로 한 channel씩 이동하고 `Shift + 좌우 방향키`로 빠르게 이동할 수 있다.

#### Wavelength range mode

- spectrum 위에서 구간을 drag해 선택한다.
- 시작 및 종료 파장을 숫자로 수정할 수 있다.
- 선택 범위에 대해 다음 계산 중 하나를 적용한다.
  - Sum
  - Mean
  - Maximum
- 선택 영역은 spectrum 위에 반투명 색상으로 표시한다.
- 양 끝 handle과 숫자 입력값은 양방향으로 동기화하고 실제 wavelength channel에 snap한다.
- range drag 중에는 가벼운 preview만 표시하고, drag 종료 또는 짧은 debounce 후 CL map을 다시 계산한다.
- 유효하지 않은 역방향/빈 range는 자동 정리하거나 즉시 안내한다.

### 5.4 CL mapping 패널

초기 mapping 종류:

- Single wavelength intensity
- Wavelength range sum
- Wavelength range mean
- Total CL intensity

후속 mapping 종류:

- Peak intensity
- Peak wavelength
- Peak FWHM
- 두 wavelength band의 ratio
- 세 wavelength band를 이용한 false-color RGB map

필수 조작 기능:

- 공통 navigation toolbar 기반 확대/축소, pan, Fit 및 1:1
- 값 hover 표시
- SE와 동일한 물리 단위의 좌표축
- SE 이미지와 view range 동기화 on/off
- linked view와 crosshair 상태를 눈에 보이게 표시
- mapping 계산 조건 표시
- map 이미지 및 수치 데이터 저장

### 5.5 SE overlay

- CL map 위에 선택한 SE 이미지를 겹쳐 표시한다.
- overlay on/off 버튼을 제공한다.
- Survey/Concurrent SE 중 overlay source를 선택할 수 있다.
- overlay opacity를 조절한다.
- blending mode를 선택할 수 있다.
  - Alpha blend
  - Multiply
  - Screen
- CL map과 SE image의 contrast를 각각 독립적으로 조절한다.
- 물리 좌표 정렬 결과가 맞지 않을 경우 수동 미세 조정 기능은 후속 버전에 추가한다.

### 5.6 Colormap과 color bar

기본 colormap 후보:

- viridis
- plasma
- inferno
- magma
- cividis
- turbo
- gray
- hot
- coolwarm
- 사용자 반전형 `_r`

설정 기능:

- colormap 선택
- color scale의 최소/최대값 직접 입력
- 전체 범위 자동 설정
- percentile 기준 자동 설정
- linear/log scale 선택
- color bar on/off
- color bar 위치 선택
- label과 unit 수정
- 글꼴 크기 및 tick 개수 조절

극단값 한두 개 때문에 map 전체 contrast가 무너지지 않도록 기본 자동 범위는 percentile 방식 사용을 권장한다.

### 5.7 Scale bar

- scale bar on/off
- 길이 자동/수동 선택
- 단위 `nm` 또는 `µm`
- 위치 선택
  - 좌측 위/아래
  - 우측 위/아래
- 색상 선택
- 두께와 글꼴 크기 조절
- 배경 box on/off
- SE와 CL map에 각각 독립적으로 설정

Scale bar 길이는 이미지 pixel count가 아닌 HDF5의 실제 pixel size를 기준으로 계산한다.

## 6. Point 및 ROI spectrum 추출

### 6.1 여러 point 선택

- Spectrum tab의 point selection CL map에서 point를 직접 추가한다.
- Mapping tab에서 point를 미리 만들 필요가 없다.
- 한 파일에 여러 point를 생성할 수 있다.
- 각 point에는 고유 색상과 이름을 부여한다.
- point marker는 원 모양을 사용한다.
- 이미지의 marker 색상과 spectrum line 색상을 동일하게 유지한다.
- point 목록에서 다음 작업을 지원한다.
  - 이름 변경
  - 표시/숨김
  - 위치 확인
  - 삭제
  - 전체 삭제
- point의 물리 좌표와 pixel 좌표를 모두 표시한다.
- single pixel 또는 `3×3`, `5×5` 주변 평균을 선택할 수 있다.

### 6.2 ROI 기능 — 추가 권장

한 점의 spectrum은 noise에 민감하므로 첫 버전부터 간단한 ROI 기능을 포함하는 것을 권장한다.

- Rectangle ROI
- Ellipse ROI
- Polygon ROI는 후속 버전
- ROI 내부 spectrum의 다음 통계를 선택한다.
  - Mean
  - Median
  - Standard deviation
- ROI 위치와 형태를 프로젝트에 저장한다.
- ROI도 Spectrum tab의 point selection map에서 생성한다.

### 6.3 Spectrum 화면

Spectrum tab 안에 CL mapping과 spectrum plot을 함께 표시한다. Mapping tab에서 point를 미리 선택할 필요 없이, Spectrum tab의 map에서 직접 여러 point를 생성하고 spectrum을 확인한다.

```text
┌──────────────┬────────────────────────┬─────────────────────────────┬───────────────────┐
│ FILES        │ POINT SELECTION MAP    │ SPECTRUM FIGURE             │ INSPECTOR         │
│              │ [Pan][Zoom][+ Point]   │ [Home][Pan][Zoom][Save]     │ ▾ Map Source      │
│ ○ File 1     │                        │               [Copy][Export]│ ▾ Points/Traces   │
│ ● File 2     │    ○ P1    ○ P2       │                             │ ▾ Overlay/Stack   │
│ ○ File 3     │          ○ P3          │                             │ ▾ Processing      │
│              │                        │                             │ ▾ Figure Style    │
└──────────────┴────────────────────────┴─────────────────────────────┴───────────────────┘
```

Spectrum tab은 `pyqtgraph CL map + embedded Matplotlib QtAgg spectrum canvas`를 한 화면에 배치한다. 화면에서 보는 spectrum figure와 export되는 publication figure가 동일한 style model을 사용하게 한다. Map, spectrum 및 inspector 폭은 splitter로 조절할 수 있으며, spectrum plot이 가장 넓은 영역을 사용한다.

#### Point selection map

- Spectrum tab을 열면 선택 파일의 현재 CL map을 표시한다.
- Mapping tab에서 마지막으로 사용한 map mode와 wavelength point/range를 초기값으로 가져온다.
- Spectrum tab의 `Map Source`에서 map mode와 wavelength 조건을 변경할 수 있다.
- Mapping tab에서 point를 생성하지 않았어도 Spectrum tab에서 바로 point를 추가할 수 있다.
- `Add Point` mode에서 map을 클릭하면 가장 가까운 CL pixel에 point를 생성한다.
- 여러 point를 연속해서 추가할 수 있다.
- 각 point marker는 원(`○`) 모양으로 표시한다.
- marker는 zoom level과 관계없이 알아보기 쉬운 일정한 screen size를 유지한다.
- sampling 범위가 single pixel, `3×3`, `5×5`인지는 원 marker와 별도로 표시한다.
- point는 `P1`, `P2`, `P3` 순서로 자동 이름을 부여하고 사용자가 변경할 수 있다.
- point를 drag해 다른 CL pixel로 이동할 수 있다.
- 선택된 point에는 흰색 또는 검은색 outer ring을 추가해 색상과 관계없이 구분한다.
- point label과 marker 표시를 각각 on/off할 수 있다.
- point 추가, 이동 및 삭제는 undo/redo를 지원한다.

Map과 spectrum의 선택 상태는 양방향으로 연동한다.

- map의 원 marker를 클릭하면 해당 spectrum line과 point row를 강조한다.
- spectrum line 또는 legend를 클릭하면 해당 원 marker를 강조하고 map 중심으로 이동할 수 있다.
- marker/line hover 시 상대 view의 항목도 동시에 강조한다.
- point 좌표는 CL pixel 좌표와 물리 좌표 `µm`를 함께 표시한다.

#### Plot navigation header

Matplotlib navigation toolbar의 검증된 기본 동작을 사용한다.

- Home/Fit
- Back/Forward view history
- Pan
- Rectangle Zoom
- Figure layout 설정
- 기본 Save
- 별도 `Copy Figure`, `Export Figure`, `Copy Data` button

Mouse wheel cursor-centered zoom과 hover 좌표 표시는 공통 GUI 규칙에 맞게 추가한다. plot이 없으면 빈 흰 화면 대신 `No spectra selected` 안내를 표시한다.

#### Traces

- Spectrum tab에서 선택한 여러 point와 ROI spectrum을 즉시 생성
- Whole-image average spectrum은 선택적으로 추가
- trace를 선택하면 plot line과 image marker를 함께 강조
- trace 순서를 drag & drop으로 변경
- 표시 이름 변경
- 각 point row에 clickable color swatch 표시
- point마다 marker/line 색상을 직접 변경
- 새 point에는 colorblind-safe palette에서 서로 다른 색상을 자동 배정
- 색상을 변경하면 map의 원 marker, spectrum line 및 legend가 동시에 갱신
- 개별 line style 및 visibility 설정
- Raw/Processed 전환
- Mean spectrum의 경우 선택적으로 standard-deviation band 표시
- `Show only selected`와 `Show all` 제공
- point를 삭제하면 marker와 spectrum line을 함께 제거하고 undo 가능

#### Overlay 및 Stacking

Spectrum 표시 mode를 명확히 구분한다.

- `Overlay`: 모든 spectrum을 같은 y축에 겹쳐 표시
- `Stack`: point 목록 순서대로 spectrum에 수직 offset을 적용해 표시
- 기본값은 `Overlay`
- `Stack offset`은 Auto 또는 수동값으로 설정
- Auto offset은 현재 spectrum들의 robust intensity span을 기준으로 계산
- point 목록을 drag & drop하면 stacking 순서도 함께 변경
- 선택적으로 각 spectrum의 baseline을 0에 맞춘 뒤 stack
- 선택적으로 separator line과 point name을 각 spectrum 옆에 표시
- stacking 중에도 point별 고유 색상을 그대로 유지
- y축 label은 `Intensity + offset`으로 자동 변경
- Stack mode는 display-only이며 원본 및 processed spectrum 값은 변경하지 않는다.
- `Copy/Export Data`는 기본적으로 offset이 없는 값을 저장하고, `Include display offsets`를 선택한 경우에만 offset column을 추가한다.
- Stack mode에서는 혼동을 막기 위해 Log y축을 비활성화하거나 Overlay 전환을 안내한다.

#### Processing

기본 plotting에 필요한 처리만 제공한다.

- Background subtraction on/off
- Savitzky–Golay smoothing on/off와 window/order
- Normalization
  - None
  - Maximum = 1
  - Area = 1
  - Exposure time
  - Exposure time × beam current
- 처리 전후 즉시 전환
- 처리 조건을 figure와 CSV metadata에 기록

처리 parameter 변경은 짧은 debounce 후 preview에 반영한다. `Reset Processing`으로 원본 표시 상태로 복원한다.

#### Axes & Scale

- x축 `Wavelength (nm)` / `Photon energy (eV)` 전환
- x/y 범위 Auto 또는 수동 입력
- y축 Linear/Log 전환
- x/y tick 표시 on/off
- tick font size와 axis border width
- axis label과 label font size
- grid on/off
- `Auto Range`와 `Reset Axes`

Photon energy 축으로 전환할 때 단순 label 변경과 spectral-density 변환을 구분한다. 첫 버전에서는 x좌표만 eV로 변환하고 y값은 기존 count임을 명확히 표시한다.

#### Line, Marker & Color

- 기본 plot mode: Line
- 선택 plot mode: Scatter, Line + Marker
- line width와 opacity
- marker 없음/원/사각형/삼각형/다이아몬드
- marker size
- trace별 직접 색상 선택
- color sequence preset: colorblind-safe, tab10, viridis sampling

1024 channel spectrum에는 marker를 기본으로 표시하지 않는다. 많은 trace가 있을 때 선택 line만 진하게 하고 나머지는 낮은 opacity로 표시한다.

#### Title, Legend & Annotation

- figure title과 font size/bold
- x/y label 수정
- legend on/off
- legend 이름, font size 및 위치
- grid on/off
- 기본 tick/label font size
- 우클릭으로 plot에 text annotation 추가
- annotation drag 이동, 내용·색상·글꼴 수정 및 삭제
- peak marker와 선택 wavelength range 음영 표시 on/off

세부 style control은 `Axes & Scale`, `Line & Marker`, `Labels & Legend`의 접히는 section으로 나눈다. 첫 화면에는 trace 선택과 자주 쓰는 axis/line 설정만 펼쳐둔다.

#### Plotting 동작

- 여러 spectrum overlay
- 선택 wavelength range 음영 표시
- peak 위치 marker 표시
- 공통 zoom/pan 규칙과 Fit to Data
- legend 또는 point 목록을 클릭해 해당 spectrum 강조/숨김
- 많은 spectrum이 표시될 때 선택된 line만 강조하고 나머지는 흐리게 표시
- style 변경은 plot data를 다시 읽지 않고 artist/style만 갱신
- processing 변경과 style 변경을 분리해 불필요한 계산 방지
- 파일을 전환해도 파일별 trace 선택과 figure style 유지
- 파일을 전환해도 파일별 point 위치, 색상, 순서 및 Overlay/Stack 설정 유지
- 현재 spectrum plot을 clipboard에 복사
- plotting 수치 데이터를 tab-separated text로 복사

#### Copy 및 저장

- `Copy Figure`: title, axes, legend 및 annotation을 포함한 300 DPI PNG를 clipboard에 복사
- `Copy Data`: 현재 보이는 trace만 tab-separated text로 복사
- `Export Figure`: PNG, SVG, PDF
- `Export Data`: spectrum CSV
- figure size와 DPI preset
- tight bounding box와 figure 크기의 약 5% outer padding
- 화면 navigation zoom과 별개로 export할 x/y range를 명시적으로 저장
- plotting에 사용한 source filename, point/ROI 이름 및 processing 조건을 metadata에 포함

저장 형식:

- PNG
- SVG
- PDF
- spectrum CSV
- plotting에 사용한 metadata 포함 CSV

#### 참고 프로그램에서 가져오지 않는 기능

SEM-CL Spectrum tab의 범위를 단순하게 유지하기 위해 다음 기능은 적용하지 않는다.

- Well/group 전용 selection
- Well/group 전용 stacking; point spectrum stacking은 지원
- Time-series 전용 color mode
- Spectrum line에 대한 custom continuous colormap editor
- 복잡한 multi-panel plate plotting

## 7. 전처리 기능

전처리는 원본 데이터를 변경하지 않고 display/analysis pipeline에만 적용한다.

권장 처리 순서:

```text
Raw uint16
→ float32 변환
→ spike/cosmic ray 처리
→ dark 또는 background 보정
→ smoothing
→ 측정 시간 및 beam current 정규화
→ mapping/spectrum 분석
```

첫 버전 필수 항목:

- 원본/처리 결과 전환
- 사용자 지정 상수 background subtraction
- background wavelength range를 이용한 offset 추정
- Savitzky–Golay smoothing on/off
- 측정 시간 정규화
- beam current 정규화

주의 사항:

- 예시 데이터의 약 300 count 수준을 항상 고정 background로 간주하지 않는다.
- spike 제거 결과는 raw spectrum과 비교할 수 있어야 한다.
- 28, 57, 230 pA 파일의 raw intensity를 직접 정량 비교하지 않는다.
- 정규화 결과의 단위를 plot과 color bar에 명확히 표시한다.

## 8. 파일 간 비교 — 후속 핵심 기능

여러 파일을 불러오는 목적을 살리기 위해 비교 tab을 후속 단계에서 구현한다.

- 여러 파일의 whole-image average spectrum 비교
- 파일별 선택 ROI spectrum 비교
- 전압, 전류, magnification 및 exposure time 조건별 grouping
- peak wavelength/intensity/FWHM 표
- 평균과 표준편차 표시
- raw counts, counts/s, counts/(s·pA), max-normalized 표시 전환

반복 측정 수가 부족할 때 공간 pixel 간 variation을 실험 반복 통계처럼 표시하지 않도록 구분한다.

## 9. 결과 내보내기

Clipboard의 `Copy`는 빠른 복사·붙여넣기에 사용하고, `Export`는 파일 형식, 해상도, 이름 및 저장 위치를 지정하는 정식 결과 저장에 사용한다.

### 9.1 이미지 및 plot

- PNG: 빠른 확인용
- SVG/PDF: 논문 및 발표용
- 해상도와 DPI 설정
- 배경 투명 여부 선택
- title, color bar, scale bar 포함 여부 선택
- 현재 SEM image, CL map, overlay 및 spectrum plot 개별 저장
- 화면 표시용 resolution과 원본 데이터 resolution 중 선택

### 9.2 수치 데이터

- point/ROI spectrum CSV
- wavelength와 energy axis 포함
- CL map TIFF 또는 NumPy array
- map 계산에 사용한 wavelength 범위 기록
- 분석 결과 요약 CSV/XLSX
- 선택 결과만 저장하거나 현재 파일의 전체 결과를 한 번에 저장
- export 파일에 source HDF5 filename과 분석 조건 포함

### 9.3 Export preset

- 현재 화면 그대로 저장
- Publication preset
- Presentation preset
- Data only

### 9.4 Export dialog

Export dialog에서 다음 항목을 한 화면에서 선택한다.

- 결과 종류
  - SEM image
  - CL map
  - SEM/CL overlay
  - Spectrum plot
  - Spectrum data
  - Point/ROI result table
  - Metadata
- 저장 형식
- image size와 DPI
- color bar, scale bar, legend 및 title 포함 여부
- 저장 폴더와 filename
- 같은 파일명이 있을 때 overwrite/rename/skip
- 선택 파일만 또는 불러온 여러 파일 batch export

기본 filename은 source filename, 결과 종류 및 파장 조건으로 자동 생성한다.

```text
NMA_5kV57pA_CLmap_700-800nm.png
NMA_5kV57pA_PointSpectra.csv
```

## 10. 프로젝트 저장과 재현성 — 추가 권장

프로젝트 파일은 원본 HDF5를 복사하지 않고 경로와 분석 상태만 저장한다.

예시 확장자:

```text
experiment.semcl.json
```

저장 내용:

- 불러온 HDF5 경로
- 파일명에서 추출하거나 사용자가 보정한 측정조건 metadata
- 파일별 active SE source
- point와 ROI 좌표
- wavelength point/range
- colormap 및 intensity range
- overlay와 scale bar 설정
- 전처리 parameter
- spectrum plot style

프로젝트를 다시 열면 이전 분석 화면을 최대한 동일하게 복원한다.

## 11. 오류 처리와 데이터 보호 — 추가 권장

- 원본 HDF5는 항상 read-only mode로 연다.
- 필수 dataset이 없으면 어떤 항목이 없는지 알려준다.
- wavelength dimension과 cube dimension이 일치하는지 검사한다.
- 비정상 wavelength, pixel size 및 NaN/Inf를 검사한다.
- 파일 로딩 실패가 다른 파일의 분석을 막지 않게 한다.
- 오래 걸리는 계산은 background worker에서 수행한다.
- 계산 중 UI가 멈추지 않게 진행률과 취소 버튼을 제공한다.
- 사용자 동작과 분석 parameter를 project log에 기록한다.

## 12. 성능 전략

- HDF5 전체를 프로그램 시작 시 모두 메모리에 올리지 않는다.
- active file의 필요한 dataset만 읽는다.
- 원본 cube는 가능하면 lazy access한다.
- 계산용 데이터는 `float32`를 기본으로 사용한다.
- 생성한 2D CL map과 평균 spectrum은 cache한다.
- wavelength 범위가 바뀌면 필요한 map만 다시 계산한다.
- 파일을 변경하면 사용하지 않는 큰 array cache를 정리한다.

현재 예시 파일 크기에서는 GPU 없이 CPU만으로 충분한 것을 기본 전제로 한다.

## 13. 기술 구성

- 언어: Python 3.12
- GUI: PySide6
- SEM/CL image와 mapping interaction: pyqtgraph
- Spectrum tab plotting: embedded matplotlib QtAgg canvas
- publication-quality figure export: matplotlib
- HDF5: h5py
- 수치 계산: NumPy, SciPy
- 이미지 처리: scikit-image
- table 및 export: pandas, openpyxl
- 환경 및 dependency 관리: uv 또는 virtual environment
- Windows 실행 파일 패키징: PyInstaller

GUI와 분석 코어를 분리해 동일한 분석 함수를 향후 batch script나 Jupyter에서도 재사용한다.

## 14. 권장 코드 구조

```text
SEM-CL/
├─ pyproject.toml
├─ README.md
├─ BLUEPRINT.md
├─ src/
│  └─ semcl_studio/
│     ├─ app.py
│     ├─ io/
│     │  ├─ hdf5_reader.py
│     │  ├─ filename_parser.py
│     │  └─ validator.py
│     ├─ models/
│     │  ├─ dataset.py
│     │  ├─ project.py
│     │  ├─ roi.py
│     │  └─ settings.py
│     ├─ processing/
│     │  ├─ background.py
│     │  ├─ despike.py
│     │  ├─ smoothing.py
│     │  └─ normalization.py
│     ├─ analysis/
│     │  ├─ spectrum.py
│     │  ├─ mapping.py
│     │  ├─ roi_analysis.py
│     │  └─ peak_fit.py
│     ├─ plotting/
│     │  ├─ image_style.py
│     │  └─ spectrum_style.py
│     ├─ export/
│     │  ├─ image_export.py
│     │  └─ data_export.py
│     └─ ui/
│        ├─ main_window.py
│        ├─ file_panel.py
│        ├─ sem_image_tab.py
│        ├─ mapping_tab.py
│        ├─ spectrum_tab.py
│        └─ widgets/
├─ tests/
└─ examples/
```

## 15. 내부 데이터 모델

```text
SemClDataset
├─ source_path
├─ survey_se[y, x]
├─ concurrent_se[y, x]
├─ cl_cube[wavelength, y, x]
├─ wavelength_nm[wavelength]
├─ spatial_scale_um
├─ offsets
├─ rotation
├─ metadata
└─ acquisition_settings
```

CL cube의 원본 HDF5 차원 `C, T, Z, Y, X` 중 크기가 1인 T/Z 차원을 안전하게 제거하고 내부에서는 `wavelength, y, x` 순서로 통일한다.

## 16. 개발 단계

### Phase 1 — 실행 가능한 기본 프로그램

- Python project 생성
- Windows에서 실행되는 main window
- 여러 HDF5 파일 추가
- 왼쪽 파일 목록 및 active file 선택
- active file의 voltage/current/magnification/exposure metadata 표시
- 예시 10개 파일 validation
- SEM Image tab과 기본 image 분석 도구
- Survey/Concurrent SE 표시
- whole-image average CL spectrum 표시

### Phase 2 — Mapping MVP

- wavelength point 선택
- wavelength range 선택
- CL map 계산
- SE image를 위쪽, CL mapping을 아래쪽에 표시
- colormap, color bar 및 scale bar
- SE overlay
- 이미지 export

### Phase 3 — Point/ROI 및 Spectrum plotting

- Spectrum tab에 CL mapping과 spectrum figure 동시 표시
- Spectrum tab의 map에서 여러 원형 point 직접 선택
- point별 marker/line 색상 연동과 변경
- ROI 평균 spectrum
- Overlay/Stack 표시와 Auto/Manual offset
- plot style 설정
- CSV 및 publication figure export

### Phase 4 — 전처리 및 정량 분석

- background correction
- spike 제거
- smoothing
- exposure/current normalization
- peak fitting과 parameter map

### Phase 5 — 파일 간 비교와 배포

- Compare tab
- 프로젝트 저장/복원
- batch export
- Windows 실행 파일 생성

## 17. 첫 버전 완료 기준

- 제공된 HDF5 예시 10개를 모두 열 수 있다.
- 여러 파일을 추가하고 왼쪽 목록에서 전환할 수 있다.
- 선택 파일의 voltage, current, magnification 및 exposure time을 확인할 수 있다.
- SEM Image tab에서 Survey/Concurrent SE를 크게 표시하고 전환할 수 있다.
- SEM image의 contrast, histogram, scale bar 및 거리 측정 기능을 사용할 수 있다.
- mouse wheel zoom이 cursor 위치를 중심으로 동작하고 image aspect ratio를 유지한다.
- Pan mode에서 point/ROI가 실수로 생성되지 않는다.
- Fit, 1:1, Reset View와 keyboard navigation이 모든 image view에서 일관되게 동작한다.
- SE와 CL의 linked zoom/pan/crosshair가 물리 좌표 기준으로 동작한다.
- 파일과 tab을 전환해도 기존 zoom, point 및 ROI 상태가 유지된다.
- 파일이 없거나 데이터가 누락된 상태에서 이해하기 쉬운 안내 화면을 표시한다.
- Survey SE와 Concurrent SE를 선택해 표시할 수 있다.
- 평균 spectrum에서 단일 파장과 파장 범위를 선택할 수 있다.
- 선택 조건에 맞는 CL map을 계산한다.
- CL map 위 SE overlay를 켜고 끌 수 있다.
- colormap, color bar, intensity 범위 및 scale bar를 조절할 수 있다.
- 여러 point에서 spectrum을 추출할 수 있다.
- Spectrum tab 한 화면에서 CL map을 보고 여러 원형 point를 직접 선택할 수 있다.
- point 색상을 변경하면 map marker, spectrum line 및 legend가 함께 변경된다.
- map marker와 spectrum line 선택 상태가 양방향으로 연동된다.
- 선택한 spectrum을 Overlay 또는 Stack mode로 즉시 표시할 수 있다.
- Stack offset Auto/Manual과 trace 순서를 조절할 수 있으며 원본 spectrum 값은 변하지 않는다.
- figure와 CSV를 저장할 수 있다.
- SEM image, CL map, spectrum plot 및 결과 table을 clipboard로 복사할 수 있다.
- 복사한 image는 PowerPoint/Word에, 수치 데이터는 Excel에 바로 붙여넣을 수 있다.
- Export dialog에서 결과 종류, 형식, 해상도 및 저장 위치를 선택할 수 있다.
- 프로그램이 원본 HDF5를 변경하지 않는다.

## 18. 기능 우선순위

### 반드시 포함

- 여러 파일 관리
- 선택 파일 분석
- SEM image 단독 표시 및 기본 분석
- SE/CL mapping
- 평균 spectrum 기반 wavelength 선택
- overlay
- colormap/color bar/scale bar
- 여러 point spectrum
- 기본 plotting 및 export
- 이미지/plot/data clipboard 복사
- 원본 보호

### 가능하면 첫 버전에 포함

- Rectangle/Ellipse ROI
- 프로젝트 저장
- background correction
- exposure/current normalization
- percentile contrast

### 후속 버전

- peak parameter map
- spectrum fitting
- 여러 파일 정량 비교
- manual image registration
- false-color CL map
- PCA/NMF 및 clustering
- 분석 report 자동 생성

## 19. 권장 기본 결정

- 탭 순서: SEM Image → Mapping → Spectrum → Compare → Export
- Mapping 화면 구성: 왼쪽 고정 파일 패널 + 중앙 SE/CL 상하 배치 + 오른쪽 Controls/Average Spectrum 상하 배치
- 화면 공간 우선순위: 중앙 SE/CL 영역 65–70%, 양쪽 보조 패널은 축소 및 숨김 가능
- GUI: PySide6
- SEM/CL 실시간 표시: pyqtgraph
- Spectrum tab 표시 및 export: embedded matplotlib QtAgg
- 기본 SE source: Concurrent SE
- 기본 CL map: 전체 wavelength sum
- 기본 colormap: viridis
- 기본 intensity range: 1–99 percentile
- 기본 scale bar: 자동 길이, 우측 아래
- 기본 point spectrum: single pixel, 필요 시 주변 평균 선택
- 원본/처리 spectrum을 항상 전환 가능하게 유지
- 모든 주요 결과에 Copy와 Export 동작을 함께 제공

이 문서를 구현 과정에서 기능 추가, 변경 이유 및 완료 여부를 기록하는 기준 문서로 사용한다.
