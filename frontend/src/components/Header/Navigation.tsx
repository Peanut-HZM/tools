export default function Navigation() {
  const navLinks = ['首页', '工具', '关于我们', '使用帮助', '反馈'];

  return (
    <nav className="hidden md:flex space-x-8">
      {navLinks.map((link) => (
        <a
          key={link}
          href="#"
          className="text-slate-300 hover:text-white transition-colors"
        >
          {link}
        </a>
      ))}
    </nav>
  );
}
