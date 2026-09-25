#!/usr/bin/env python3
"""Compare cache spanning-read data, latency and snoop behavior with baseline."""
from pathlib import Path
import argparse
import subprocess
r=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--cache',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
d=a.out.resolve();d.mkdir(parents=True,exist_ok=True)
s=(r/'rtl/ap68040/tb/tb_ap040_cache_snoop.v').read_text()
s=s.replace('else m_rdata <= mem[m_addr[15:2]];', '''else if (cross_model) m_rdata <= cross_value(m_addr,m_size); else m_rdata <= mem[m_addr[15:2]];''')
s=s.replace('integer errors = 0;', '''integer errors = 0;
reg cross_model=0;
integer cross_checks=0, cross_matrix=0, cross_wrap, cross_warm, cross_kind;
reg [31:0] cross_base, cross_expected;
function [31:0] cross_value(input [31:0] a,input [1:0] sz);
reg [63:0] v;
begin
 v={mem[a[15:2]],mem[a[15:2]+1]};v=v<<(8*a[1:0]);
 cross_value=(sz==0)?{24'd0,v[63:56]}:(sz==1)?{16'd0,v[63:48]}:v[63:32];
end
endfunction
integer span_checks=0, span_offset, span_phase, span_base;
reg [63:0] span_pair;
reg [31:0] span_expected;
''')
block=r'''
    // Prime a known line, then cover every within-line longword span.
    @(negedge clk);
    mem['hC800>>2]='h11223344; mem['hC804>>2]='h55667788;
    mem['hC808>>2]='h99AABBCC; mem['hC80C>>2]='hDDEEFF00;
    snoop('hC800);
    cpu_read_count_sized('hC800, 2'b10, d, normal_cycles);
    repeat(24) @(posedge clk);
    for(span_offset=1;span_offset<12;span_offset=span_offset+1) begin
      if((span_offset%4)!=0) begin
        @(negedge clk); c_addr='hC800+span_offset;
        repeat(2) @(posedge clk);
        span_pair={mem[('hC800+span_offset)>>2],mem[(('hC800+span_offset)>>2)+1]};
        span_pair=span_pair << (8*(span_offset%4));
        span_expected=span_pair[63:32];
        span_base=mread_count;
        cpu_read_count_sized('hC800+span_offset,2'b10,d,normal_cycles);
        if(d!==span_expected || mread_count!=span_base) begin
          $display("FAIL explicit span offset=%0d data=%h expected=%h",span_offset,d,span_expected);errors++;
        end
        $display("SPAN offset=%0d cycles=%0d",span_offset,normal_cycles);
        span_checks++;
        if((span_offset%4)==3) begin
          cpu_read_count_sized('hC800+span_offset,2'b01,d,normal_cycles);
          if(d!=={16'd0,span_expected[31:16]}) begin $display("FAIL explicit word span");errors++;end
          span_checks++;
        end
      end
    end
    // Snoop at admission, or during the early line-read assembly window.
    for(span_phase=0;span_phase<3;span_phase++) begin
      @(negedge clk);mem['hC804>>2]='h55667788;snoop('hC800);
      cpu_read_count_sized('hC800,2'b10,d,normal_cycles);
      repeat(24) @(posedge clk);
      @(negedge clk);c_addr='hC802;
      repeat(2) @(posedge clk);
      fork
        begin
          cpu_read_count_sized('hC802,2'b10,d,normal_cycles);
          if(d!==32'h3344ABCD) begin $display("FAIL span snoop phase=%0d data=%h",span_phase,d);errors++;end
        end
        begin
          @(negedge clk);
          repeat(span_phase == 0 ? 0 : 1) @(negedge clk);
          if(span_phase==2) begin ce_run=0; repeat(2) @(negedge clk); end
          mem['hC804>>2]='hABCDEF01;s_addr='hC800;s_stb=1;
          @(negedge clk);s_stb=0;
          if(span_phase==2) begin repeat(2) @(negedge clk);ce_run=1;end
        end
      join
      span_checks++;
    end

    cross_model=1;

    // Cold first line, cold second line, and double hit; repeat at set wrap.
    for(cross_wrap=0;cross_wrap<2;cross_wrap++) begin
      cross_base=cross_wrap ? 'h1FF0 : 'hC800;
      for(cross_warm=0;cross_warm<3;cross_warm++) begin
        for(cross_kind=0;cross_kind<4;cross_kind++) begin
          @(negedge clk);
          mem[(cross_base+12)>>2]='h11223344;
          mem[(cross_base+16)>>2]='hAABBCCDD;
          snoop(cross_base);snoop(cross_base+16);
          if(cross_warm>0) begin
            cpu_read_count_sized(cross_base+12,2'b10,d,normal_cycles);
            repeat(24) @(posedge clk);
          end
          if(cross_warm>1) begin
            cpu_read_count_sized(cross_base+16,2'b10,d,normal_cycles);
            repeat(24) @(posedge clk);
          end
          span_offset=(cross_kind==3)?15:13+cross_kind;
          case(cross_kind)
            0:cross_expected='h223344AA;
            1:cross_expected='h3344AABB;
            2:cross_expected='h44AABBCC;
            3:cross_expected='h000044AA;
          endcase
          @(negedge clk);c_addr=cross_base+span_offset;
          repeat(2) @(posedge clk);span_base=mread_count;
          cpu_read_count_sized(cross_base+span_offset,(cross_kind==3)?2'b01:2'b10,d,normal_cycles);
          if(d!==cross_expected || (cross_warm==2 && mread_count!=span_base)) begin
            $display("FAIL cross matrix wrap=%0d warm=%0d kind=%0d data=%h expected=%h",cross_wrap,cross_warm,cross_kind,d,cross_expected);errors++;
          end
          $display("CROSS_MATRIX wrap=%0d warm=%0d kind=%0d cycles=%0d",cross_wrap,cross_warm,cross_kind,normal_cycles);
          cross_matrix++;
          repeat(24) @(posedge clk);
        end
      end
    end
    $display("EXPLICIT_CROSS_MATRIX checks=%0d",cross_matrix);

    for(span_phase=0;span_phase<3;span_phase++) begin
      @(negedge clk);
      mem['hC80C>>2]='h11223344;mem['hC810>>2]='h55667788;
      snoop('hC800);snoop('hC810);
      cpu_read_count_sized('hC80C,2'b10,d,normal_cycles);
      repeat(24) @(posedge clk);
      cpu_read_count_sized('hC810,2'b10,d,normal_cycles);
      repeat(24) @(posedge clk);
      @(negedge clk);c_addr='hC80E;
      repeat(2) @(posedge clk);
      fork
        begin
          cpu_read_count_sized('hC80E,2'b10,d,normal_cycles);
          if(d!==32'h3344ABCD) begin $display("FAIL cross snoop phase=%0d data=%h",span_phase,d);errors++;end
        end
        begin
          @(negedge clk);
          repeat(span_phase == 0 ? 0 : 1) @(negedge clk);
          if(span_phase==2) begin ce_run=0;repeat(2) @(negedge clk);end
          mem['hC810>>2]='hABCDEF01;s_addr='hC810;s_stb=1;
          @(negedge clk);s_stb=0;
          if(span_phase==2) begin repeat(2) @(negedge clk);ce_run=1;end
        end
      join
      cross_checks++;
    end
    $display("EXPLICIT_CROSS checks=%0d",cross_checks);
    $display("EXPLICIT_SPANS checks=%0d",span_checks);
'''
needle='\tif (errors == 0) $display("ALL TESTS PASSED");'
assert s.count(needle)==1
s=s.replace(needle,block+'\n'+needle)
(d/'spans_tb.v').write_text(s)
for name,cache in [('candidate',a.cache.resolve()),('baseline',r/'rtl/ap68040/rtl/ap040_cache.v')]:
 with (d/(name+'_spans_compile.log')).open('w') as f:
  subprocess.run(['iverilog','-g2012','-I',str(r/'rtl/ap68040/rtl'),'-s','tb_ap040_cache_snoop','-o',str(d/(name+'_spans.vvp')),str(d/'spans_tb.v'),str(cache),str(r/'rtl/ap68040/rtl/primitives/dpram.v')],stdout=f,stderr=subprocess.STDOUT,check=True)
 with (d/(name+'_spans.log')).open('w') as f:subprocess.run(['vvp',str(d/(name+'_spans.vvp'))],stdout=f,stderr=subprocess.STDOUT,check=True)
 log=(d/(name+'_spans.log')).read_text()
 print(name,'\n'.join(x for x in log.splitlines() if x.startswith(('SPAN','EXPLICIT','FAIL','ALL TESTS'))),flush=True)
 assert 'ALL TESTS PASSED' in log and 'FAIL' not in log and 'EXPLICIT_SPANS checks=15' in log and 'EXPLICIT_CROSS checks=3' in log and 'EXPLICIT_CROSS_MATRIX checks=24' in log
