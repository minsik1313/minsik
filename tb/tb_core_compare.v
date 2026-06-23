// =============================================================================
//  tb_core_compare.v
//  ISA 기반 멀티사이클 CPU(cpu_core) vs SIMT GPU(gpu_core) 비교 테스트벤치
//
//  cpu_vec/gpu_vec(단순 비교판)와 달리, 여기서는 실제 "프로그램"이
//  명령어 메모리에서 fetch 되어 실행된다:
//    - CPU : LI/LW/MUL/SW/ADDI/BNE 로 작성된 소프트웨어 루프
//    - GPU : 같은 ISA, 분기 없는 커널을 P개 lane 에 SIMT 로 동시 발행
//
//  두 설계에 동일한 입력 벡터를 데이터 메모리에 적재하고, 완료까지 걸린
//  사이클 수와 결과(C 영역)를 비교한다.
// =============================================================================
`timescale 1ns / 1ps

module tb_core_compare #(
    parameter integer N      = 16,     // 벡터 길이 (커맨드라인 -P 로 override 가능)
    parameter integer P      = 4,      // GPU lane 수
    parameter integer CLK_NS = 10
);

    localparam integer DMEM_DEPTH = 3*N;
    localparam integer DAW    = $clog2(DMEM_DEPTH);

    reg clk, rst, cpu_start, gpu_start;

    // ----- CPU 코어 + 단일 포트 데이터 메모리 -----
    wire cpu_busy, cpu_done;
    wire [31:0] cpu_cycles, cpu_instrs;
    wire cpu_we;
    wire [DAW-1:0] cpu_addr;
    wire [31:0] cpu_wdata, cpu_rdata;

    cpu_core #(.N(N), .DMEM_DEPTH(DMEM_DEPTH)) u_cpu (
        .clk(clk), .rst(rst), .start(cpu_start),
        .busy(cpu_busy), .done(cpu_done),
        .cycle_count(cpu_cycles), .instr_count(cpu_instrs),
        .dmem_we(cpu_we), .dmem_addr(cpu_addr),
        .dmem_wdata(cpu_wdata), .dmem_rdata(cpu_rdata)
    );

    sync_mem #(.WIDTH(32), .DEPTH(DMEM_DEPTH)) u_cpu_dmem (
        .clk(clk), .we(cpu_we), .addr(cpu_addr),
        .wdata(cpu_wdata), .rdata(cpu_rdata)
    );

    // ----- GPU 코어 + P포트 데이터 메모리 -----
    wire gpu_busy, gpu_done;
    wire [31:0] gpu_cycles, gpu_instrs;
    wire [P-1:0] gpu_we;
    wire [P*DAW-1:0] gpu_addr_flat;
    wire [P*32-1:0] gpu_wdata_flat, gpu_rdata_flat;

    gpu_core #(.N(N), .P(P), .DMEM_DEPTH(DMEM_DEPTH)) u_gpu (
        .clk(clk), .rst(rst), .start(gpu_start),
        .busy(gpu_busy), .done(gpu_done),
        .cycle_count(gpu_cycles), .instr_count(gpu_instrs),
        .dmem_we(gpu_we), .dmem_addr_flat(gpu_addr_flat),
        .dmem_wdata_flat(gpu_wdata_flat), .dmem_rdata_flat(gpu_rdata_flat)
    );

    sync_mem_mp #(.WIDTH(32), .DEPTH(DMEM_DEPTH), .PORTS(P)) u_gpu_dmem (
        .clk(clk), .we(gpu_we), .addr_flat(gpu_addr_flat),
        .wdata_flat(gpu_wdata_flat), .rdata_flat(gpu_rdata_flat)
    );

    always #(CLK_NS/2) clk = ~clk;

    // ----- 입력 벡터 / golden -----
    integer i, errors;
    reg [31:0] a_vec [0:N-1];
    reg [31:0] b_vec [0:N-1];
    reg [31:0] golden [0:N-1];

    task setup_and_load;
        begin
            for (i = 0; i < N; i = i + 1) begin
                a_vec[i]  = $random % 256; if (a_vec[i][31]) a_vec[i] = -a_vec[i];
                b_vec[i]  = $random % 256; if (b_vec[i][31]) b_vec[i] = -b_vec[i];
                golden[i] = a_vec[i] * b_vec[i];
            end
            // 두 데이터 메모리에 동일한 A,B 적재 (testbench 의 계층참조를 통한 직접 poke)
            for (i = 0; i < N; i = i + 1) begin
                u_cpu_dmem.mem[i]     = a_vec[i];
                u_cpu_dmem.mem[N+i]   = b_vec[i];
                u_gpu_dmem.mem[i]     = a_vec[i];
                u_gpu_dmem.mem[N+i]   = b_vec[i];
            end
        end
    endtask

    task run_cpu;
        begin
            @(negedge clk); cpu_start = 1'b1;
            @(negedge clk); cpu_start = 1'b0;
            wait (cpu_done);
            @(negedge clk);
        end
    endtask

    task run_gpu;
        begin
            @(negedge clk); gpu_start = 1'b1;
            @(negedge clk); gpu_start = 1'b0;
            wait (gpu_done);
            @(negedge clk);
        end
    endtask

    task check_results;
        reg [31:0] cval, gval;
        begin
            errors = 0;
            for (i = 0; i < N; i = i + 1) begin
                cval = u_cpu_dmem.mem[2*N+i];
                gval = u_gpu_dmem.mem[2*N+i];
                if (cval !== golden[i]) begin
                    $display("  [FAIL] CPU C[%0d] = %0d, expected %0d", i, cval, golden[i]);
                    errors = errors + 1;
                end
                if (gval !== golden[i]) begin
                    $display("  [FAIL] GPU C[%0d] = %0d, expected %0d", i, gval, golden[i]);
                    errors = errors + 1;
                end
            end
        end
    endtask

    initial begin
        $dumpfile("sim/wave_core.vcd");
        $dumpvars(0, tb_core_compare);

        clk = 0; rst = 1; cpu_start = 0; gpu_start = 0;
        repeat (3) @(negedge clk);
        rst = 0;

        setup_and_load;

        $display("================================================================");
        $display(" ISA-based Multicycle CPU vs SIMT GPU  --  C[i] = A[i] * B[i]");
        $display(" N = %0d elements, GPU lanes P = %0d, clock = %0d ns", N, P, CLK_NS);
        $display("================================================================");
        $display(" Index :    A     B   ->  golden(A*B)");
        for (i = 0; i < N; i = i + 1)
            $display("   [%2d] : %4d  %4d  ->  %6d", i, a_vec[i], b_vec[i], golden[i]);
        $display("----------------------------------------------------------------");

        run_cpu;
        $display(" CPU  done : %0d cycles, %0d instructions executed  =>  %0d ns",
                  cpu_cycles, cpu_instrs, cpu_cycles*CLK_NS);

        run_gpu;
        $display(" GPU  done : %0d cycles, %0d instruction-slots issued =>  %0d ns",
                  gpu_cycles, gpu_instrs, gpu_cycles*CLK_NS);

        $display("----------------------------------------------------------------");
        check_results;
        if (errors == 0)
            $display(" RESULT VERIFY : PASS  (CPU == GPU == golden, all %0d elements)", N);
        else
            $display(" RESULT VERIFY : FAIL  (%0d mismatches)", errors);

        $display("----------------------------------------------------------------");
        $display(" TIMING COMPARISON");
        $display("   CPU : %0d cycles (%0d ns)  -- %0d instrs x 4 cycles/instr (multicycle)",
                  cpu_cycles, cpu_cycles*CLK_NS, cpu_instrs);
        $display("   GPU : %0d cycles (%0d ns)  -- %0d blocks x 5 instrs x 4 cycles + block-init",
                  gpu_cycles, gpu_cycles*CLK_NS, (N+P-1)/P);
        if (gpu_cycles > 0)
            $display("   Speedup (GPU vs CPU) : %0d.%02d x",
                      cpu_cycles / gpu_cycles, ((cpu_cycles*100)/gpu_cycles) % 100);
        $display(" GPU executes %0d lanes in parallel AND skips per-element loop/branch", P);
        $display(" overhead (no ADDI/BNE per element) -> speedup can exceed P.");
        $display("================================================================");

        if (errors == 0) $display(" >>> TEST PASSED <<<");
        else              $display(" >>> TEST FAILED <<<");

        #20 $finish;
    end

    initial begin
        #200000;
        $display(" [TIMEOUT] simulation did not finish in time");
        $finish;
    end

endmodule
