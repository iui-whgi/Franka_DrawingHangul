
# 1. 개발환경

Python
IsaacSim 4.5.0, Visual Studio Code
Ubuntu 22.04
LangGraph Package: langchain, langchain-core, langchain-community, langchain-openai, langchain-text-splitters, langgraph, langgraph-checkpoint, langgraph-sdk, openai, streamlit, tiktoken


Simulation 파일은 IsaacSim 4.5 우분투 22.04 환경에서 다운로드후 IsaacSim 폴더 안 하위디렉토리로 만든 후 에 main.py 파일을 실행시키면 됩니다.


---
# 2. 진행 과정 및 문제점
초기에는 x축을 고정한 상태에서 y축과 z축을 움직이며 벽면에 글자를 쓰는 방식으로 구현을 시도하였다. 그러나 이 경우, 로봇의 입장에서 더 많은 액추에이터의 각도 제어가 요구되어 동작이 복잡해졌고, 결과적으로 z축을 고정한 채 바닥에 글자를 그리는 방식으로 전환하였다. 이는 로봇이 보다 자연스럽고 효율적으로 움직일 수 있는 방향으로 판단되었기 때문이다.

또한, IsaacSim에서 획득한 8개의 액추에이터 각도 값을 Gazebo 시뮬레이션 환경에서 재현하고자 하였으나, 초반부에서 로봇의 특이점(singularity) 문제로 인해 오류가 발생하였다. 이후, 수집된 데이터의 약 200 step 이후 구간부터 실제 환경에 적용하자 문제 없이 동작하였으며, 실제 Franka 로봇 역시 정상적으로 작동하였다. 일반적인 강화학습 기반 제어 방식은 시작 단계부터 경로 계획(path planning)을 수립하지만, 본 프로젝트에서는 z축의 바닥 부근에 위치한 획의 시작점으로 먼저 도달하는 동작이 우선되어 있었으며, 이로 인해 초기에는 단순 낙하 동작만이 수행되었기 때문으로 판단된다.

Sim2Real 전환은 전반적으로 안정적으로 이루어졌으나, 실제 로봇이 화이트보드에 글씨를 쓰는 과정에서 z축이 고정되조 못하고 미세한 출렁임이 발생하였다. 이로 인해 글씨가 정확히 쓰이지 않았으며, 이는 로봇 특이점을 회피하는 과정에서 z축 제어에 과도한 제약이 걸렸기 때문으로 분석된다.


---
# 3. 향후 계획
현재 시스템은 기능적으로는 정상 동작하지만, 구조적으로는 다소 파편화되어 있어 유지보수 및 재현성 측면에서 비효율적인 문제가 존재한다. 따라서 추후에는 Docker 환경 내에 LangChain 및 IsaacSim을 통합하여, 보다 일관성 있고 재현 가능한 구조를 구성할 계획이다. 이를 통해 JSON 파일을 자동 생성하고, 실험 반복과 결과 관리의 효율성을 극대화할 수 있을 것으로 기대된다.



https://github.com/user-attachments/assets/2b261361-0e96-4bcc-a99e-f3d27e3e9694



![Screenshot from 2025-03-26 15-09-52](https://github.com/user-attachments/assets/7b3151c2-5350-48b9-8beb-c918f1cd1b44)


![Screenshot from 2025-03-28 20-29-36](https://github.com/user-attachments/assets/0a2222e2-60f1-484d-b497-a086b350d925)
