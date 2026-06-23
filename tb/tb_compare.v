// =============================================================================
//  tb_compare.v
//  CPU(순차) vs GPU(병렬) 벡터 연산기 비교 테스트벤치
//
//  1) 동일한 입력 벡터 A, B 를 두 설계에 인가
//  2) 각 설계의 동작 사이클 수(=연산 시간)를 측정
//  3) 두 설계의 결과가 서로 같은지, 그리고 소프트웨어 golden 값과
//     일치하는지 검증
//  4) 속도(사이클/시간) 비교 및 speedup 출력
// =============================================================================
`timescale 1ns / 1ps

module tb_compare #(
    // ----- 파라미터 (커맨드라인 -P 로 override 가능) -----
    parameter integer N      = 16,    // 벡터 길이
    parameter integer DW     = 8,     // 원소 비트 폭
    parameter integer P      = 4,     // GPU 병렬 PE 수
    parameter integer CLK_NS = 10     // 클록 주기 10ns (100MHz)
);

    // ----- 공통 신호 -----
    reg                  clk;
    reg                  rst;
    reg  [N*DW-1:0]      a_flat;
    reg  [N*DW-1:0]      b_flat;

    // CPU 측 신호
    reg                  cpu_start;
    wire [N*2*DW-1:0]    cpu_c;
    wire                 cpu_busy, cpu_done;

    // GPU 측 신호
    reg                  gpu_start;
    wire [N*2*DW-1:0]    gpu_c;
    wire                 gpu_busy, gpu_done;

    // 측정/검증용
    integer cpu_cycles, gpu_cycles;
    integer i, errors;
    reg [2*DW-1:0] golden [0:N-1];

    // ----- DUT 인스턴스 -----
    cpu_vec #(.N(N), .DW(DW)) u_cpu (
        .clk(clk), .rst(rst), .start(cpu_start),
        .a_flat(a_flat), .b_flat(b_flat),
        .c_flat(cpu_c), .busy(cpu_busy), .done(cpu_done)
    );

    gpu_vec #(.N(N), .DW(DW), .P(P)) u_gpu (
        .clk(clk), .rst(rst), .start(gpu_start),
        .a_flat(a_flat), .b_flat(b_flat),
        .c_flat(gpu_c), .busy(gpu_busy), .done(gpu_done)
    );

    // ----- 클록 생성 -----
    always #(CLK_NS/2) clk = ~clk;

    // ----- 입력 벡터 준비 + 소프트웨어 golden 계산 -----
    task setup_vectors;
        integer k;
        reg [DW-1:0] av, bv;
        begin
            a_flat = 0;
            b_flat = 0;
            for (k = 0; k < N; k = k + 1) begin
                av = $random;            // 8비트 랜덤
                bv = $random;
                a_flat[k*DW +: DW] = av;
                b_flat[k*DW +: DW] = bv;
                golden[k] = av * bv;     // 기대값
            end
        end
    endtask

    // ----- CPU 실행 + 사이클 측정 -----
    task run_cpu;
        begin
            @(negedge clk);
            cpu_start = 1'b1;
            @(negedge clk);
            cpu_start = 1'b0;
            cpu_cycles = 0;
            // busy 가 풀리고 done 이 뜰 때까지 클록 카운트
            while (!cpu_done) begin
                @(posedge clk);
                cpu_cycles = cpu_cycles + 1;
            end
        end
    endtask

    // ----- GPU 실행 + 사이클 측정 -----
    task run_gpu;
        begin
            @(negedge clk);
            gpu_start = 1'b1;
            @(negedge clk);
            gpu_start = 1'b0;
            gpu_cycles = 0;
            while (!gpu_done) begin
                @(posedge clk);
                gpu_cycles = gpu_cycles + 1;
            end
        end
    endtask

    // ----- 결과 검증 -----
    task check_results;
        reg [2*DW-1:0] cval, gval;
        begin
            errors = 0;
            for (i = 0; i < N; i = i + 1) begin
                cval = cpu_c[i*2*DW +: 2*DW];
                gval = gpu_c[i*2*DW +: 2*DW];
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

    // ----- 메인 시퀀스 -----
    initial begin
        $dumpfile("sim/wave.vcd");
        $dumpvars(0, tb_compare);

        // 초기화
        clk       = 1'b0;
        rst       = 1'b1;
        cpu_start = 1'b0;
        gpu_start = 1'b0;
        a_flat    = 0;
        b_flat    = 0;
        repeat (3) @(negedge clk);
        rst = 1'b0;

        // 입력 준비
        setup_vectors;

        $display("================================================================");
        $display(" CPU(Sequential) vs GPU(Parallel) Vector Multiply  C = A * B");
        $display(" N = %0d elements, DW = %0d bit, GPU lanes P = %0d", N, DW, P);
        $display(" Clock period = %0d ns (%0d MHz)", CLK_NS, 1000/CLK_NS);
        $display("================================================================");

        // 입력 벡터 출력
        $display(" Index :   A    B   ->  golden(A*B)");
        for (i = 0; i < N; i = i + 1)
            $display("   [%2d] : %3d  %3d  ->  %5d",
                     i, a_flat[i*DW +: DW], b_flat[i*DW +: DW], golden[i]);
        $display("----------------------------------------------------------------");

        // CPU 실행
        run_cpu;
        $display(" CPU  done : %0d cycles  =>  %0d ns", cpu_cycles, cpu_cycles*CLK_NS);

        // GPU 실행
        run_gpu;
        $display(" GPU  done : %0d cycles  =>  %0d ns", gpu_cycles, gpu_cycles*CLK_NS);

        // 검증
        $display("----------------------------------------------------------------");
        check_results;
        if (errors == 0)
            $display(" RESULT VERIFY : PASS  (CPU == GPU == golden, all %0d elements)", N);
        else
            $display(" RESULT VERIFY : FAIL  (%0d mismatches)", errors);

        // 시간 비교
        $display("----------------------------------------------------------------");
        $display(" TIMING COMPARISON");
        $display("   CPU  : %0d cycles (%0d ns)", cpu_cycles, cpu_cycles*CLK_NS);
        $display("   GPU  : %0d cycles (%0d ns)", gpu_cycles, gpu_cycles*CLK_NS);
        if (gpu_cycles > 0)
            $display("   Speedup (GPU vs CPU) : %0d.%02d x",
                     cpu_cycles / gpu_cycles,
                     ((cpu_cycles*100) / gpu_cycles) % 100);
        $display(" GPU uses %0d parallel PEs -> theoretical speedup ~ %0dx", P, P);
        $display("================================================================");

        if (errors == 0)
            $display(" >>> TEST PASSED <<<");
        else
            $display(" >>> TEST FAILED <<<");

        #20 $finish;
    end

    // 안전장치: 타임아웃
    initial begin
        #100000;
        $display(" [TIMEOUT] simulation did not finish in time");
        $finish;
    end

endmodule
