library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library ftl;
use ftl.ftlbase.all;
use work.comp_tslink_ct.all;

entity tb1 is
end entity;

architecture arch of tb1 is

signal eos : boolean := false;
signal    clk :   std_ulogic;
signal    rst :  std_ulogic;
signal    LinkIn :  std_ulogic;
signal    IValid :  std_ulogic;
signal    QAck :  std_ulogic;
signal    IData :  std_logic_vector(7 downto 0);
signal    IAck :  std_ulogic;
signal    ShiftEnable : std_ulogic;
signal    LinkOut : std_ulogic;
signal    QValid : std_ulogic;

begin

    dut: tslink_ct
    port map (
        clk, -- : in  std_ulogic;
        rst, -- : in  std_ulogic;
        LinkIn, -- : in std_ulogic;
        IValid, -- : in std_ulogic;
        QAck, -- : in std_ulogic;
        IData, -- : in std_logic_vector(7 downto 0);
        IAck, -- : out std_ulogic;
        ShiftEnable, -- : out std_ulogic;
        LinkOut, -- : out std_ulogic;
        QValid -- : out std_ulogic
    );

    clkgen: process
    begin
        clk <= '0'; wait for 5 ns; clk <= '1'; wait for 5 ns; clk <= '0';
        if eos then
            wait;
        end if;
    end process;

    tb: process
    begin
        rst <= '1';
        LinkIn <= '0';
        IValid <= '0';
        QAck <= '0';
        IData <= x"00";
        wait until rising_edge(clk);

        rst <= '0';
        wait until rising_edge(clk);

        IData <= x"A5";
        IValid <= '1';
        wait until rising_edge(clk);

        -- LinkIn <= '1';
        wait until rising_edge(clk);

        LinkIn <= '0';
        wait until rising_edge(clk);

        wait until rising_edge(clk);
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        wait until rising_edge(clk);


        eos <= true;
        wait;
    end process;





end architecture ; -- arch
