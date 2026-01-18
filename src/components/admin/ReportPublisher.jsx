import React, { useState } from 'react';
import { Copy, Check, FileText, Send, Share2 } from 'lucide-react';
import { marked } from 'marked';

export default function ReportPublisher({ reports }) {
  const [copiedId, setCopiedId] = useState(null);

  const handleCopyMd = async (report) => {
    try {
      await navigator.clipboard.writeText(report.content);
      setCopiedId(`${report.id}-md`);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  };

  const handleCopyHtml = async (report) => {
    try {
      // 简单的 Markdown 转 HTML，适配公众号格式
      const htmlContent = marked(report.content);
      // 增加一些内联样式以适应公众号
      const styledHtml = `<div style="font-size: 16px; line-height: 1.6; color: #333;">${htmlContent}</div>`;
      
      // 复制 HTML 需要使用 Clipboard API 的特殊方式（text/html）
      // 这里简化处理，先复制纯文本 HTML，实际公众号编辑器通常粘贴富文本需要更复杂处理
      // 更好的方式是展示一个预览框让用户复制
      await navigator.clipboard.writeText(htmlContent); // 暂时复制源码
      
      setCopiedId(`${report.id}-html`);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  };

  const handlePublish = (platform) => {
    alert(`正在开发中：发布到 ${platform}`);
  };

  return (
    <div className="space-y-6">
      {reports.map((report) => (
        <div key={report.id} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-gray-100 flex justify-between items-center">
            <div>
              <h3 className="text-lg font-semibold text-gray-800">{report.report_date} 日报</h3>
              <p className="text-sm text-gray-500 mt-1">创建于 {new Date(report.created_at).toLocaleString('zh-CN')}</p>
            </div>
            <div className="flex gap-2">
              <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">已生成</span>
            </div>
          </div>
          
          <div className="p-6 bg-gray-50 flex flex-wrap gap-4">
            <div className="flex gap-2">
              <button
                onClick={() => handleCopyMd(report)}
                className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                {copiedId === `${report.id}-md` ? <Check className="w-4 h-4 text-green-600" /> : <FileText className="w-4 h-4" />}
                {copiedId === `${report.id}-md` ? '已复制' : '复制 Markdown'}
              </button>
              
              <button
                onClick={() => handleCopyHtml(report)}
                className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                {copiedId === `${report.id}-html` ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                {copiedId === `${report.id}-html` ? '已复制' : '复制 HTML'}
              </button>
            </div>

            <div className="w-px h-10 bg-gray-300 mx-2 hidden sm:block"></div>

            <div className="flex gap-2">
               <button
                onClick={() => handlePublish('知乎')}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                <Share2 className="w-4 h-4" />
                发布到知乎
              </button>
               <button
                onClick={() => handlePublish('微信公众号')}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
              >
                <Send className="w-4 h-4" />
                发布到公众号
              </button>
            </div>
          </div>

          <div className="p-6 bg-white border-t border-gray-100">
             <div className="max-h-40 overflow-y-auto text-sm text-gray-600 bg-gray-50 p-4 rounded-lg font-mono">
                {report.content.substring(0, 300)}...
             </div>
          </div>
        </div>
      ))}
    </div>
  );
}
