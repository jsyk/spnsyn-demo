
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library ftl;
use ftl.ftlbase.all;
use work.comp_tslink_ct.all;

entity tslink is
port (
    clk : in  std_ulogic;
    rst : in  std_ulogic;
    LinkIn : in std_ulogic;
    IValid : in std_ulogic;
    QAck : in std_ulogic;
    IData : in std_logic_vector(7 downto 0);
    IAck : out std_ulogic;
    QData : out std_logic_vector(7 downto 0);
    LinkOut : out std_ulogic;
    QValid : out std_ulogic
);
end entity;


architecture rtl of tslink is
signal    ShiftEnable : std_ulogic;
signal  s_qdata : std_logic_vector(7 downto 0);
begin
    ct: tslink_ct
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

    shifter: process (clk)
    begin
        if rising_edge(clk) then
            if rst='1' then
                s_qdata <= (others => '0');
            else
                if ShiftEnable='1' then
                    s_qdata <= LinkIn & s_qdata(7 downto 1);
                end if;
            end if;
        end if;
    end process;

    QData <= s_qdata;
end architecture rtl;

------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library ftl;
use ftl.ftlbase.all;
use work.comp_tslink_ct.all;

entity tb2 is
end entity;

architecture arch of tb2 is

component tslink is
port (
    clk : in  std_ulogic;
    rst : in  std_ulogic;
    LinkIn : in std_ulogic;
    IValid : in std_ulogic;
    QAck : in std_ulogic;
    IData : in std_logic_vector(7 downto 0);
    IAck : out std_ulogic;
    QData : out std_logic_vector(7 downto 0);
    LinkOut : out std_ulogic;
    QValid : out std_ulogic
);
end component;

signal eos : boolean := false;
signal    clk :   std_ulogic;
signal    rst :  std_ulogic;

signal    LinkIn :  std_ulogic;
signal    LinkOut : std_ulogic;

signal    IValid_1 :  std_ulogic;
signal    QAck_1 :  std_ulogic;
signal    IData_1 :  std_logic_vector(7 downto 0);
signal    IAck_1 :  std_ulogic;
signal    QData_1 : std_logic_vector(7 downto 0);
signal    QValid_1 : std_ulogic;

signal    IValid_2 :  std_ulogic;
signal    QAck_2 :  std_ulogic;
signal    IData_2 :  std_logic_vector(7 downto 0);
signal    IAck_2 :  std_ulogic;
signal    QData_2 : std_logic_vector(7 downto 0);
signal    QValid_2 : std_ulogic;


begin

    dut1: tslink
    port map (
        clk, -- : in  std_ulogic;
        rst, -- : in  std_ulogic;
        LinkIn, -- : in std_ulogic;
        IValid_1, -- : in std_ulogic;
        QAck_1, -- : in std_ulogic;
        IData_1, -- : in std_logic_vector(7 downto 0);
        IAck_1, -- : out std_ulogic;
        QData_1,
        LinkOut, -- : out std_ulogic;
        QValid_1 -- : out std_ulogic
    );

    dut2: tslink
    port map (
        clk, -- : in  std_ulogic;
        rst, -- : in  std_ulogic;
        LinkOut, -- : in std_ulogic;
        IValid_2, -- : in std_ulogic;
        QAck_2, -- : in std_ulogic;
        IData_2, -- : in std_logic_vector(7 downto 0);
        IAck_2, -- : out std_ulogic;
        QData_2,
        LinkIn, -- : out std_ulogic;
        QValid_2 -- : out std_ulogic
    );

    clkgen: process
    begin
        clk <= '0'; wait for 5 ns; clk <= '1'; wait for 5 ns; clk <= '0';
        if eos then
            wait;
        end if;
    end process;

    tb1: process
    begin
        rst <= '1';
        IValid_1 <= '0';
        QAck_1 <= '0';
        IData_1 <= x"00";
        wait until rising_edge(clk);
        rst <= '0';
        wait until rising_edge(clk);

        IData_1 <= x"A5";
        IValid_1 <= '1';
        wait until rising_edge(clk) and IAck_1='1';
        IValid_1 <= '0';

        wait until rising_edge(clk) and QValid_1='1';
        QAck_1 <= '1';
        wait until rising_edge(clk);
        QAck_1 <= '0';

        wait until rising_edge(clk);

        IData_1 <= x"12";
        IValid_1 <= '1';
        wait until rising_edge(clk) and QValid_1='1';
        QAck_1 <= '1';
        wait until rising_edge(clk) and IAck_1='1';
        IValid_1 <= '0';
        QAck_1 <= '0';

        wait for 30 ns;
        eos <= true;
        wait;
    end process;

    tb2: process
    begin
        IValid_2 <= '0';
        QAck_2 <= '0';
        IData_2 <= x"00";
        wait until rising_edge(clk);
        wait until rising_edge(clk);

        wait until rising_edge(clk) and QValid_2='1';
        QAck_2 <= '1';
        wait until rising_edge(clk);
        QAck_2 <= '0';

        IData_2 <= x"5A";
        IValid_2 <= '1';
        wait until rising_edge(clk) and IAck_2='1';
        IValid_2 <= '0';

        wait until rising_edge(clk);


        IData_2 <= x"23";
        IValid_2 <= '1';
        wait until rising_edge(clk) and QValid_2='1';
        QAck_2 <= '1';
        wait until rising_edge(clk) and IAck_2='1';
        IValid_2 <= '0';
        QAck_2 <= '0';

        wait;
    end process;

end architecture ; -- arch
