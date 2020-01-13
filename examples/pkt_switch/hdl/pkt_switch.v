
//Simple pkt switch, functionality:
// - 1 data input interface, 2 data output interfaces
// - data width is 8 bits, with "valid" bit
// - packet is tranmitted continuously (valid = 1, cannot fall in the middle)
// - when valid = 0 that means a gap between packets, packet always starts when valid 0->1
// - first byte of the packet is address, second is packet length (in bytes), following by the data
// - non-filtered packets are transmitted on interface 0, filtered on 1
// - if filtering is not enabled, packets are simply forwarded on interface 0
// - 1 control interface (write only)
// - registers:
// - ADDR:         FUNCTIONALITY:
// - 000           settings:
//                            bit 0 - enable address-based filtering
//                            bit 1 - enable length-based filtering 
//                            bit 2 - transmit packet on both interfaces
// - 010           address for address-based filtering  
// - 011           address based filtering mask (which bits of the address are valid)
// - 100           lower size limit for length based filtering
// - 101           uppoer size limit for length based filtering

module pkt_switch (
  clk, 
  rst_n, 
  datain_data, 
  datain_valid, 
  dataout0_data, 
  dataout1_data, 
  dataout0_valid, 
  dataout1_valid,
  ctrl_addr,
  ctrl_data,
  ctrl_wr
);

  input clk, rst_n;
  //data interfaces
  input [7:0] datain_data;
  input datain_valid;
  output reg [7:0] dataout0_data, dataout1_data;
  output reg dataout0_valid, dataout1_valid;
  //control interface
  input [2:0] ctrl_addr;
  input [7:0] ctrl_data;
  input ctrl_wr; 

  //config registers
  reg addr_filtering_ena_r;
  reg len_filtering_ena_r;  
  reg transmit_both_ena_r; 

  reg [7:0] filter_addr_r;
  reg [7:0] filter_addr_mask_r;
  reg [7:0] lower_size_limit_r;
  reg [7:0] upper_size_limit_r;

  reg [7:0] data_0_r, data_1_r;
  reg datain_valid_0_r, datain_valid_1_r;
  reg [7:0] pkt_addr_r, pkt_len_r;

  wire channel0_active, channel1_active;

  always @(posedge clk or negedge rst_n)  
  begin : config_proc
    if(~rst_n) begin
      addr_filtering_ena_r <= 1'b0;
      len_filtering_ena_r <= 1'b0;
      transmit_both_ena_r <= 1'b0;
      filter_addr_r <= 8'd0;
      filter_addr_mask_r <= 8'd0;
      lower_size_limit_r <= 8'd0;
      upper_size_limit_r <= 8'd0;
    end else if (ctrl_wr) begin
      case (ctrl_addr)
        3'b000: begin
          addr_filtering_ena_r <= ctrl_data[0];
          len_filtering_ena_r <= ctrl_data[1];
          transmit_both_ena_r <= ctrl_data[2];
        end
        3'b010: filter_addr_r <= ctrl_data;
        3'b011: filter_addr_mask_r <= ctrl_data;
        3'b100: lower_size_limit_r <= ctrl_data;
        3'b101: upper_size_limit_r <= ctrl_data;
      endcase
    end  
  end

  always @(posedge clk or negedge rst_n)  
  begin : data_proc
    if(~rst_n) begin
      data_0_r <= 8'd0;
      data_1_r <= 8'd0;
      dataout0_data <= 8'd0;
      dataout1_data <= 8'd0;
      datain_valid_0_r <= 1'b0;
      datain_valid_1_r <= 1'b0;
    end else begin
      data_0_r <= datain_data;
      data_1_r <= data_0_r;
      datain_valid_0_r <= datain_valid;
      datain_valid_1_r <= datain_valid_0_r;
      dataout0_data <= (channel0_active) ? data_1_r : 8'd0;
      dataout0_valid <= (channel0_active) ? datain_valid_1_r : 1'b0;
      dataout1_data <= (channel1_active) ? data_1_r : 8'd0;
      dataout1_valid <= (channel1_active) ? datain_valid_1_r : 1'b0;
    end
  end

  always @(posedge clk or negedge rst_n)  
  begin : header_proc
    if(~rst_n) begin
      pkt_addr_r <= 8'd0;
      pkt_len_r <= 8'd0;
    end else begin
      if (datain_valid && !datain_valid_0_r) //first packet byte
        pkt_addr_r <= datain_data;
      if (datain_valid_0_r && !datain_valid_1_r) //second packet byte
        pkt_len_r <= datain_data;
    end
  end

  assign addr_filtering_active = 
    addr_filtering_ena_r &&        
    ((pkt_addr_r & filter_addr_mask_r) == (filter_addr_r & filter_addr_mask_r));
  assign len_filtering_active =
    len_filtering_ena_r &&
    ((pkt_len_r >= lower_size_limit_r) && (pkt_len_r <= upper_size_limit_r));

  assign channel0_active = 
    !addr_filtering_active && !len_filtering_active;
  assign channel1_active =
    transmit_both_ena_r || 
    addr_filtering_active || len_filtering_active;

endmodule
