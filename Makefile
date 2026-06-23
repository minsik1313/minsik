# =============================================================================
#  Makefile : CPU(순차) vs GPU(병렬) RTL 시뮬레이션
#
#   make            기본 설정(N=16, P=4)으로 컴파일 + 실행
#   make sweep      N 을 16->64->256->1024 로 키우며 speedup 변화 관찰
#   make wave       파형(wave.vcd) 생성 후 gtkwave 안내
#   make clean      산출물 삭제
# =============================================================================

IV      = iverilog
VVP     = vvp
IVFLAGS = -g2012
SRC     = rtl/cpu/cpu_vec.v rtl/gpu/gpu_vec.v tb/tb_compare.v
TOP     = tb_compare
SIMDIR  = sim

.PHONY: all run sweep wave clean

all: run

# 기본 실행 (N=16, DW=8, P=4)
run: $(SIMDIR)/compare.vvp
	@$(VVP) $(SIMDIR)/compare.vvp

$(SIMDIR)/compare.vvp: $(SRC)
	@mkdir -p $(SIMDIR)
	@$(IV) $(IVFLAGS) -o $@ $(SRC)

# N 을 키우면서 GPU speedup 이 이론치(P)에 수렴함을 확인
sweep:
	@mkdir -p $(SIMDIR)
	@for n in 16 64 256 1024 ; do \
		echo "" ; \
		echo "########################  N = $$n  ########################" ; \
		$(IV) $(IVFLAGS) -P$(TOP).N=$$n -o $(SIMDIR)/sweep_$$n.vvp $(SRC) ; \
		$(VVP) $(SIMDIR)/sweep_$$n.vvp | grep -E "CPU |GPU |Speedup|VERIFY|N =" ; \
	done

wave: run
	@echo "파형 파일 생성됨: $(SIMDIR)/wave.vcd"
	@echo "보기:  gtkwave $(SIMDIR)/wave.vcd"

clean:
	@rm -rf $(SIMDIR)
	@echo "cleaned."
