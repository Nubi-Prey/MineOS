package dev.evvie.waylandcraft.mixin;

import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import net.minecraft.client.DeltaTracker;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.GameRenderer;

@Mixin(GameRenderer.class)
public class GameRendererMixin {

    @Shadow
    @Final
    private Minecraft minecraft;

    @Inject(method = "renderLevel", at = @At("HEAD"), cancellable = true)
    private void waylandcraft$guardNullPlayerOnRenderLevel(DeltaTracker deltaTracker, CallbackInfo ci) {
        if (this.minecraft == null || this.minecraft.player == null) {
            ci.cancel();
        }
    }
}
