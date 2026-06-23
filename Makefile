# =============================================================================
#  Makefile : CPU vs GPU RTL 시뮬레이션
#
#  [v1] 단순 비교판 - 단일 MAC(CPU) vs 병렬 MAC(GPU)
#   make            기본 설정(N=16, P=4)으로 컴파일 + 실행
#   make sweep      N 을 16->64->256->1024 로 키우며 speedup 변화 관찰
#   make wave       파형(sim/wave.vcd) 생성 후 gtkwave 안내
#
#  [v2] ISA 기반 멀티사이클 CPU vs SIMT GPU (실제 구조에 더 가까움)
#   make run2       기본 설정(N=16, P=4)으로 컴파일 + 실행
#   make sweep2     N 을 16->17->64->67 로 키우며(배수/비배수 포함) 검증
#   make wave2      파형(sim/wave_core.vcd) 생성
#
#   make clean      산출물 삭제
# =============================================================================

IV      = iverilog
VVP     = vvp
IVFLAGS = -g2012
SIMDIR  = sim

# ----- v1: 단순 비교판 -----
SRC1    = rtl/cpu/cpu_vec.v rtl/gpu/gpu_vec.v tb/tb_compare.v
TOP1    = tb_compare

# ----- v2: ISA 기반 멀티사이클/SIMT 비교판 -----
SRC2    = rtl/common/sync_mem.v rtl/common/sync_mem_mp.v \
          rtl/cpu/cpu_core.v rtl/gpu/gpu_core.v tb/tb_core_compare.v
TOP2    = tb_core_compare
IVFLAGS2 = -g2012 -I rtl/common

.PHONY: all run sweep wave run2 sweep2 wave2 clean

all: run run2

# 기본 실행 (N=16, DW=8, P=4)
run: $(SIMDIR)/compare.vvp
	@$(VVP) $(SIMDIR)/compare.vvp

$(SIMDIR)/compare.vvp: $(SRC1)
	@mkdir -p $(SIMDIR)
	@$(IV) $(IVFLAGS) -o $@ $(SRC1)

# N 을 키우면서 GPU speedup 이 이론치(P)에 수렴함을 확인
sweep:
	@mkdir -p $(SIMDIR)
	@for n in 16 64 256 1024 ; do \
		echo "" ; \
		echo "########################  N = $$n  ########################" ; \
		$(IV) $(IVFLAGS) -P$(TOP1).N=$$n -o $(SIMDIR)/sweep_$$n.vvp $(SRC1) ; \
		$(VVP) $(SIMDIR)/sweep_$$n.vvp | grep -E "CPU |GPU |Speedup|VERIFY|N =" ; \
	done

wave: run
	@echo "파형 파일 생성됨: $(SIMDIR)/wave.vcd"
	@echo "보기:  gtkwave $(SIMDIR)/wave.vcd"

# 기본 실행 (N=16, P=4) - ISA 기반 CPU/GPU 코어
run2: $(SIMDIR)/core_compare.vvp
	@$(VVP) $(SIMDIR)/core_compare.vvp

$(SIMDIR)/core_compare.vvp: $(SRC2)
	@mkdir -p $(SIMDIR)
	@$(IV) $(IVFLAGS2) -o $@ $(SRC2)

# N 의 배수/비배수 케이스를 모두 포함해 검증 + speedup 변화 관찰
sweep2:
	@mkdir -p $(SIMDIR)
	@for n in 16 17 64 67 ; do \
		echo "" ; \
		echo "########################  N = $$n  ########################" ; \
		$(IV) $(IVFLAGS2) -P$(TOP2).N=$$n -o $(SIMDIR)/core_sweep_$$n.vvp $(SRC2) ; \
		$(VVP) $(SIMDIR)/core_sweep_$$n.vvp | grep -E "CPU  done|GPU  done|Speedup|VERIFY" ; \
	done

wave2: run2
	@echo "파형 파일 생성됨: $(SIMDIR)/wave_core.vcd"
	@echo "보기:  gtkwave $(SIMDIR)/wave_core.vcd"

clean:
	@rm -rf $(SIMDIR)
	@echo "cleaned."
