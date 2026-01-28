import React, { useState } from 'react';
import { Menu, X, ExternalLink } from 'lucide-react';

interface Link {
  href: string;
  label: string;
  icon: string;
}

const links: Link[] = [
  { href: '/daily/trending', label: '热点速览', icon: '🔥' },
  { href: '/daily/tech', label: '技术前沿', icon: '💻' },
  { href: '/daily/business', label: '商业洞察', icon: '💼' },
  { href: '/github', label: 'GitHub 趋势', icon: '⭐' },
  { href: '/huggingface', label: 'HuggingFace', icon: '🤗' },
];

interface Props {
  baseUrl: string;
}

export default function MobileMenu({ baseUrl }: Props) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="md:hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 text-slate-500 hover:text-slate-900 focus:outline-none"
        aria-label="Toggle menu"
      >
        {isOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {isOpen && (
        <div className="absolute top-16 left-0 right-0 bg-white border-b border-slate-200 shadow-lg p-4 flex flex-col gap-2 z-50 animate-in slide-in-from-top-2 duration-200">
          {links.map(link => (
            <a
              key={link.href}
              href={`${baseUrl}${link.href}`}
              className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-slate-50 text-slate-700 font-medium transition-colors"
              onClick={() => setIsOpen(false)}
            >
              <span className="text-xl">{link.icon}</span>
              {link.label}
            </a>
          ))}
          <div className="border-t border-slate-100 my-2 pt-2">
            <a
              href={`${baseUrl}/`}
              className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-slate-50 text-slate-500 text-sm"
              onClick={() => setIsOpen(false)}
            >
              返回首页
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
