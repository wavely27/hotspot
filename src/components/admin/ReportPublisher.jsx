import React, { useState } from 'react';
import { Copy, Check, FileText, Send, Share2 } from 'lucide-react';
import { marked } from 'marked';

const WECHAT_STYLES = {
  container: `font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif; font-size: 16px; line-height: 1.8; color: #333; padding: 10px;`,
  h1: `font-size: 22px; font-weight: bold; color: #1f2937; margin: 24px 0 16px; border-bottom: 2px solid #3b82f6; padding-bottom: 8px;`,
  h2: `font-size: 18px; font-weight: bold; color: #1f2937; margin: 20px 0 12px; border-left: 4px solid #3b82f6; padding-left: 10px;`,
  h3: `font-size: 16px; font-weight: bold; color: #374151; margin: 16px 0 8px;`,
  p: `margin: 0 0 16px; text-align: justify;`,
  a: `color: #3b82f6; text-decoration: none; border-bottom: 1px dashed #3b82f6;`,
  blockquote: `margin: 16px 0; padding: 12px 16px; background: #f3f4f6; border-left: 4px solid #9ca3af; color: #555; font-size: 15px; border-radius: 4px;`,
  ul: `margin: 0 0 16px; padding-left: 20px;`,
  li: `margin-bottom: 8px;`,
  strong: `color: #2563eb; font-weight: bold;`,
  code: `background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-family: Menlo, Monaco, Consolas, monospace; font-size: 14px; color: #c2410c;`
};

const renderer = {
  heading({ text, depth }) {
    const style = WECHAT_STYLES[`h${depth}`] || WECHAT_STYLES.h3;
    return `<h${depth} style="${style}">${text}</h${depth}>`;
  },
  paragraph({ tokens }) {
    const text = this.parser.parseInline(tokens);
    return `<p style="${WECHAT_STYLES.p}">${text}</p>`;
  },
  link({ href, text }) {
    return `<a href="${href}" style="${WECHAT_STYLES.a}">${text}</a>`;
  },
  blockquote({ tokens }) {
    const body = this.parser.parse(tokens);
    return `<blockquote style="${WECHAT_STYLES.blockquote}">${body}</blockquote>`;
  },
  list({ items, ordered }) {
    const type = ordered ? 'ol' : 'ul';
    const body = items.map(item => this.listitem(item)).join('');
    return `<${type} style="${WECHAT_STYLES.ul}">${body}</${type}>`;
  },
  listitem({ tokens }) {
    const text = this.parser.parse(tokens);
    return `<li style="${WECHAT_STYLES.li}">${text}</li>`;
  },
  strong({ text }) {
    return `<strong style="${WECHAT_STYLES.strong}">${text}</strong>`;
  },
  codespan({ text }) {
    return `<code style="${WECHAT_STYLES.code}">${text}</code>`;
  }
};

marked.use({ renderer });

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
      const bodyHtml = marked(report.content);
      
      const fullHtml = `<div style="${WECHAT_STYLES.container}">${bodyHtml}<hr style="margin: 30px 0; border: 0; border-top: 1px solid #eee;" /><p style="text-align: center; font-size: 14px; color: #888;">本文由 AI 自动生成，内容仅供参考</p></div>`;

      const blobHtml = new Blob([fullHtml], { type: 'text/html' });
      const blobText = new Blob([report.content], { type: 'text/plain' });
      
      const data = [new ClipboardItem({
        'text/html': blobHtml,
        'text/plain': blobText,
      })];

      await navigator.clipboard.write(data);
      
      setCopiedId(`${report.id}-html`);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy rich text', err);
      try {
        const simpleHtml = marked(report.content);
        await navigator.clipboard.writeText(simpleHtml);
        setCopiedId(`${report.id}-html`);
        alert('富文本复制失败，已复制 HTML 源码。请手动粘贴。');
        setTimeout(() => setCopiedId(null), 2000);
      } catch (e) {
        alert('复制失败，请手动复制。');
      }
    }
  };

  const handlePublish = (platform) => {
    alert(`对于订阅号，请使用"复制公众号格式"按钮，然后在微信后台粘贴即可。\n\n目前${platform} API 仅支持认证服务号。`);
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
                {copiedId === `${report.id}-html` ? '已复制' : '复制公众号格式'}
              </button>
            </div>

            <div className="w-px h-10 bg-gray-300 mx-2 hidden sm:block"></div>

            <div className="flex gap-2">
               <button
                onClick={() => handlePublish('微信公众号')}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
              >
                <Send className="w-4 h-4" />
                使用说明
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
