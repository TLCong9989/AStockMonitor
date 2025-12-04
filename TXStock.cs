using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.IO;
using System.Net;
using System.Drawing;
using System.Threading;
using Investment_Assistant428. MODEL;
using Investment_Assistant428.DAO;
using System.Globalization;
using System.Text.RegularExpressions;
namespace Investment_Assistant428
{
    class TXStock
    {
        //获取批量股票的信息
        //codes 代码列表
        public static string[] getStockInfo(string codes)
        {
             string[] msgs={};
             if (!codes.Contains('s') && !codes.Contains('b'))
             {
                codes= StringEdit.spstrsformat(codes.Split(',').ToList());
             }
             try
             {
                 //string url = "http://hq.sinajs.cn/list="+code;
                 //http://qt.gtimg.cn/q=sz000858
                 string url = "http://qt.gtimg.cn/q=" + codes;
                 WebClient client = new WebClient();
                 client.Headers.Add("Content-Type", "text/html; charset=gb2312");
                 Stream data = client.OpenRead(url);
                 StreamReader reader = new StreamReader(data, Encoding.GetEncoding("gb2312"));
                 while (reader == null)
                 {
                     Thread.Sleep(5000);
                     Console.WriteLine("为空拉" + DateTime.Now.ToLongTimeString());
                     reader = new StreamReader(data, Encoding.GetEncoding("gb2312"));
                 }
                 string str = reader.ReadToEnd();
                 List<TXStock> stockList = new List<TXStock>();//股票信息列表
                 msgs = StringEdit.strsSqlit(str);//返回股票详情的数组
                 //Console.WriteLine(DateTime.Now.ToString("HH:mm:ss:fff"));
                 //Console.WriteLine(msgs[0]);
                 reader.Close();
                 data.Close();

             }
             catch (Exception e)
             { Console.WriteLine("读取出错了"+e.Message);
            msgs= getStockInfo(codes);
             }

             return msgs;
        }

        public static void getZS(string codes)
        {
           

            string code = "899050";   // 上证指数
            string date = "20230103";
            string date2 = "20250926";

            string url = "https://q.stock.sohu.com/hisHq?code=zs_"
                       + code.ToLower()
                       + "&start=" + date
                       + "&end=" + date2;

            /* 1. 拉数据 */
            string json = new WebClient().DownloadString(url);

            //int p1 = json.IndexOf("\"hq\":") + 5;
            //int p2 = json.IndexOf("]", p1) + 1;
            //string hqChunk = json.Substring(p1, p2 - p1);
            // 匹配 \" 和 \" 之间的内容
           // var matches = Regex.Matches(json, "\"([^\"]*)\"");
            var matchall = Regex.Matches(json, @"\[([^\[\]]*)\]");//根据[]匹配

            foreach (Match match in matchall)
            {
                var matches = Regex.Matches(match.Groups[1].Value, "\"([^\"]*)\"");
                /* 4. 解析 */
                DateTime d = DateTime.ParseExact(matches[0].Value.Replace("\"", ""), "yyyy-MM-dd", CultureInfo.InvariantCulture);//日期
                double open = double.Parse(matches[1].Value.Replace("\"", ""), CultureInfo.InvariantCulture);//开盘点数
                double close = double.Parse(matches[2].Value.Replace("\"", ""), CultureInfo.InvariantCulture);//收盘点数
                double changePct = double.Parse(matches[4].Value.Replace("\"", "").TrimEnd('%'), CultureInfo.InvariantCulture);//涨跌百分比
                double low = double.Parse(matches[5].Value.Replace("\"", ""), CultureInfo.InvariantCulture);   // 最低点数
                double high = double.Parse(matches[6].Value.Replace("\"", ""), CultureInfo.InvariantCulture);  // 最高点数
                long volume = long.Parse(matches[7].Value.Replace("\"", "")) / 10000;//成交量
                double amount = Math.Round(double.Parse(matches[8].Value.Replace("\"", ""), CultureInfo.InvariantCulture) / 10000, 2);//成交额
                string sc = "";
                if (code == "000001") { sc = "上证"; }
                if (code == "399001") { sc = "深圳"; }
                if (code == "399006") { sc = "创业板"; }
                if (code == "899050") { sc = "北交所"; }
                /* 5. 填充新 Model */
                MarketIndex mi = new MarketIndex
                {
                    Sctype = sc,
                    Nowtime = d,
                    Redopennum = 0,                                  // 指数无明细
                    Redclosenum = 0,
                    Upnum = 0,
                    Zeronum = 0,
                    Fallnum = 0,
                    Turnover = volume,
                    Buymoney = amount,
                    Openpercent = 0,        // 当日振幅（开盘→收盘）
                    Closepercent = 0,                          // 收盘涨跌幅
                    Openpoint = open,
                    Closepoint = close,
                    Highpoint = high,
                    Lowpoint = low,
                    Risepercent = changePct
                };
                string sql = string.Format(
  CultureInfo.InvariantCulture,
  "INSERT INTO marketindex (sctype,nowtime,redopennum,redclosenum,upnum,zeronum,fallnum,turnover,buymoney,openpercent,closepercent,openpoint,closepoint,highpoint,lowpoint,risepercent) VALUES ('{0}','{1:yyyy-MM-dd}',{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15})",
  mi.Sctype,
  mi.Nowtime,
  mi.Redopennum,
  mi.Redclosenum,
  mi.Upnum,
  mi.Zeronum,
  mi.Fallnum,
  mi.Turnover,
  mi.Buymoney,
  mi.Openpercent,
  mi.Closepercent,
  mi.Openpoint,
  mi.Closepoint,
  mi.Highpoint,
  mi.Lowpoint,
  mi.Risepercent);
                MarketIndexDAO mid = new MarketIndexDAO();
                int i = mid.ZSGSQL(sql); ;
                Console.WriteLine(i+""); 
            }




          

    //        Console.WriteLine(sql);
              
            
        }

        public static string[] getStockInfo(List<string> codes)
        {
            if (codes != null && codes.Count > 0 && !codes[0].Contains('s'))
            { 
            
            }
            string[] msgs={};
            string sel300 = "";
            string[] stocks = {};
            int i = 0;
            int j = 0;
            for ( i = 0; i < Form1.staticLStock.Count; i += 300)
            {
                sel300 = "";
                for ( j = i; j < i + 300 && j < codes.Count; j++)
                {
                    if (sel300 != "") { sel300 += ","; }
                    sel300 += codes[j];
                }
                if(j >= codes.Count)
                {
                     stocks = TXStock.getStockInfo(sel300);//获取已经拆分后的股票字符数组
                     msgs = msgs.Concat(stocks).ToArray();
                    return msgs;
                }
                 stocks = TXStock.getStockInfo(sel300);//获取已经拆分后的股票字符数组
                 msgs = msgs.Concat(stocks).ToArray();
            }

            return msgs;
        }


        public static Image getpic(string codes)
        {
            return null;
           //string url= http://image.sinajs.cn/newchart/daily/n/sh601006.gif;
        }
    }
}
