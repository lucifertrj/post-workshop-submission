import Link from "next/link";

export default function Home() {
  return (
    <main className="relative">
      {/* Top nav */}
      <nav className="flex items-center justify-between px-8 py-6 text-sm font-mono">
        <span className="text-cream tracking-tight">proximal methods</span>
        <div className="flex gap-6 text-muted">
          <Link href="/deblur" className="hover:text-gold transition-colors">
            deblur
          </Link>
          <Link href="/denoise" className="hover:text-gold transition-colors">
            recover
          </Link>
          <Link href="/race" className="hover:text-gold transition-colors">
            race
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="min-h-[88vh] flex flex-col items-center justify-center px-8 text-center">
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-muted mb-8">
          Optimization Techniques · 2026
        </p>
        <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight max-w-4xl mb-6 leading-[1.05]">
          Proximal Methods
          <br />
          <span className="text-gold">in Practice</span>
        </h1>
        <p className="text-lg sm:text-xl text-muted max-w-2xl mb-12 leading-relaxed">
          A visual comparison of <span className="text-cream">ISTA</span> and{" "}
          <span className="text-cream">FISTA</span> on image deblurring with
          total-variation regularization and sparse signal recovery via LASSO.
        </p>
        <div className="flex flex-col sm:flex-row gap-4">
          <Link
            href="/deblur"
            className="px-8 py-3 rounded-full bg-gold text-deep font-medium hover:opacity-90 transition-opacity"
          >
            Try Deblurring →
          </Link>
          <Link
            href="/denoise"
            className="px-8 py-3 rounded-full border border-cream/25 text-cream hover:border-cream/60 hover:bg-cream/5 transition-all"
          >
            Try Sparse Recovery →
          </Link>
        </div>
      </section>

      {/* Math panel */}
      <section className="px-8 py-32 max-w-3xl mx-auto">
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-muted mb-4">
          the framework
        </p>
        <h2 className="text-3xl sm:text-4xl font-semibold mb-8 leading-tight">
          One algorithm family,
          <br />
          two non-smooth regularizers.
        </h2>
        <p className="text-muted mb-8 leading-relaxed">
          Both demos optimize a composite objective F(x) = f(x) + g(x), where
          f is smooth (gradient is L-Lipschitz) and g is non-smooth but admits
          a tractable proximal operator. The proximal-gradient family iterates:
        </p>
        <pre className="font-mono text-xs sm:text-sm bg-deep/60 border border-line rounded-lg p-5 sm:p-6 overflow-x-auto leading-relaxed tabular text-cream/90">
{`F(x) = f(x) + g(x)

ISTA    x_{k+1} = prox_{αg}( x_k − α ∇f(x_k) )

FISTA   y_k     = x_k + β_k · (x_k − x_{k−1})
        x_{k+1} = prox_{αg}( y_k − α ∇f(y_k) )
        t_{k+1} = (1 + √(1 + 4·t_k²)) / 2
        β_k     = (t_k − 1) / t_{k+1}`}
        </pre>
        <p className="text-muted mt-8 leading-relaxed text-sm">
          ISTA converges at rate{" "}
          <span className="font-mono text-cream">O(1/k)</span>; FISTA's
          momentum sequence{" "}
          <span className="font-mono text-cream">t_k</span>{" "}
          (Beck &amp; Teboulle, 2009) accelerates it to{" "}
          <span className="font-mono text-cream">O(1/k²)</span>. On the demos
          below this shows up as roughly a{" "}
          <span className="text-gold">3–4× speedup</span> in iterations to
          reach a given objective tolerance.
        </p>
      </section>

      {/* Two-card demo grid */}
      <section className="px-8 pb-32 max-w-5xl mx-auto grid sm:grid-cols-2 gap-6">
        <DemoCard
          href="/deblur"
          tag="demo · 2D"
          title="Image Deblurring"
          desc="Recover a sharp image from a blurry, noisy observation using total-variation regularization. Live convergence curves; PSNR/SSIM tracked per iteration."
          equation="min_x  ½‖A x − y‖²  +  λ · TV(x)"
        />
        <DemoCard
          href="/denoise"
          tag="demo · 1D"
          title="Sparse Recovery (LASSO)"
          desc="Recover a sparse signal from compressed Gaussian measurements. Soft thresholding in action; SNR and sparsity tracked per iteration."
          equation="min_x  ½‖A x − y‖²  +  λ · ‖x‖₁"
        />
      </section>

      <footer className="px-8 pb-12 text-center font-mono text-xs text-muted">
        Beck &amp; Teboulle (2009) · Daubechies-Defrise-De Mol (2004) ·
        Chambolle (2004) · Parikh &amp; Boyd (2014)
      </footer>
    </main>
  );
}

function DemoCard({
  href,
  tag,
  title,
  desc,
  equation,
}: {
  href: string;
  tag: string;
  title: string;
  desc: string;
  equation: string;
}) {
  return (
    <Link
      href={href}
      className="group block p-8 rounded-2xl border border-line bg-deep/40 hover:bg-deep/70 hover:border-cream/30 transition-all"
    >
      <p className="font-mono text-xs uppercase tracking-[0.3em] text-muted mb-3">
        {tag}
      </p>
      <h3 className="text-2xl font-semibold mb-3">{title}</h3>
      <p className="text-muted leading-relaxed mb-6 text-sm">{desc}</p>
      <pre className="font-mono text-xs text-cream/80 bg-deep/60 px-3 py-2 rounded border border-line overflow-x-auto">
        {equation}
      </pre>
      <span className="mt-6 inline-block font-mono text-sm text-gold opacity-0 group-hover:opacity-100 transition-opacity">
        run →
      </span>
    </Link>
  );
}
